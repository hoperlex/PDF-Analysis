"""`W54-TRANSPORT-01` -- the inbound key's forced command refuses every guard and every
grammar violation, and the bundle that crosses it is the bundle that was sent.

Under test: `infra/deploy/receive-bundle.sh` (the stand side of the inbound key),
`infra/deploy/push-bundle.sh` (this side) and `infra/deploy/lib/forced-command.sh` (the
dispatcher and the one bundle-tree rule both ends apply). `W54-PLAN.md` §3.5 and §4.

**The shape of each guard case is `test_deploy_script_refusals.py`'s.** For every guard
marked `# >>> guard: <name>` in the three files:

1. an invocation that should trip it exits 3 and prints `REFUSED [<name>]`;
2. the same invocation against a copy with exactly that guard block deleted no longer
   prints `REFUSED [<name>]`. A message can come from an unreachable guard; a deletion
   cannot be faked.

A guard with no case here, or a case with no guard, reddens
`test_every_guard_has_a_case_here`; a verb registered without a grammar-violation case
reddens `test_every_verb_has_grammar_violation_cases`. That is the "a guard without a case
is red" rule later lanes inherit when they add a verb (`W54-STAND-COPY-01`,
`W57A-STANDOPS-01`).

**Nothing here reaches a daemon, a network or a stand.** `docker` and `ssh` are replaced on
`PATH` by stubs that record their arguments; the `ssh` stub can hand its stdin and its
remote command to a staged copy of `receive-bundle.sh`, which is exactly what sshd does
with a forced command, so the round trip is real bytes through real `tar` and
`sha256sum` with no socket. Staging, the copy record and the checkout all live under
`tmp_path`.

**What stdin offset proves.** The script's stdin is an open file shared with this process,
so after it exits the file offset says how many bytes it consumed. A refusal "before
reading" is an offset of 0.
"""

from __future__ import annotations

import fcntl
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import tarfile
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
DEPLOY = ROOT / "infra/deploy"
RECEIVE = DEPLOY / "receive-bundle.sh"
PUSH = DEPLOY / "push-bundle.sh"
LIB = DEPLOY / "lib/forced-command.sh"

#: The three files, by their path under `infra/deploy/`, as the stage lays them out.
SCRIPTS = {
    "receive-bundle.sh": RECEIVE,
    "push-bundle.sh": PUSH,
    "lib/forced-command.sh": LIB,
}

REFUSED = 3

#: The real corpus's base key (`docs/program`, 13 citations) and the shape the repair run
#: gives it (`W54-PLAN.md` §3.3: 121 repairs; `+<m>u` whenever m > 0).
BASE_KEY = "2026-07-23..2026-08-20+17d.4b74348debf7"
REPAIRED_KEY = "2026-07-23..2026-08-20+17d+121r+3u.4b74348debf7"

#: The tar `push-bundle.sh` produces, flag for flag (pinned against the script below).
TAR_FLAGS = (
    "--create", "--format=gnu", "--sort=name", "--owner=0", "--group=0", "--numeric-owner",
    "--mtime=@0", "--hard-dereference", "--mode=u+rwX,go+rX,go-w",
)

DOCKER_STUB = r'''#!/usr/bin/env python3
"""A `docker` that records, optionally waits for a release file, and reaches nothing."""
import json
import os
import sys
import time

with open(os.environ["STUB_LOG"], "a", encoding="utf-8") as handle:
    handle.write(json.dumps(sys.argv[1:]) + "\n")
if sys.argv[1:2] == ["compose"] and sys.argv[6:7] == ["ps"]:
    # `W54-STAND-COPY-01`: which writer has a running container, from STUB_RUNNING.
    if sys.argv[-1] in os.environ.get("STUB_RUNNING", "").split(","):
        sys.stdout.write("cid-" + sys.argv[-1] + "\n")
    sys.exit(0)
release = os.environ.get("STUB_RELEASE")
if release:
    deadline = time.time() + 20
    while not os.path.exists(release) and time.time() < deadline:
        time.sleep(0.05)
sys.stdout.write(os.environ.get("STUB_STDOUT", "stub module output") + "\n")
sys.exit(int(os.environ.get("STUB_EXIT", "0")))
'''

SSH_STUB = r'''#!/usr/bin/env python3
"""An `ssh` that records, and -- like sshd with a forced command -- hands its remote
command and its stdin to the staged receive-bundle.sh. It opens no socket."""
import json
import os
import subprocess
import sys

with open(os.environ["SSH_LOG"], "a", encoding="utf-8") as handle:
    handle.write(json.dumps(sys.argv[1:]) + "\n")
forward = os.environ.get("SSH_FORWARD")
if not forward:
    sys.stdin.buffer.read()
    sys.exit(0)
env = dict(os.environ, SSH_ORIGINAL_COMMAND=sys.argv[-1])
sys.exit(subprocess.run(["bash", forward], env=env).returncode)
'''


# --- the stage ------------------------------------------------------------------------


@dataclass
class Stand:
    """A clone-shaped checkout, a staging directory and a copy record, all under tmp."""

    root: Path
    deploy: Path
    staging: Path
    record: Path
    env_file: Path
    bin: Path
    docker_log: Path
    ssh_log: Path

    @property
    def receive(self) -> Path:
        return self.deploy / "receive-bundle.sh"

    @property
    def push(self) -> Path:
        return self.deploy / "push-bundle.sh"

    def docker_calls(self) -> list[list[str]]:
        if not self.docker_log.exists():
            return []
        return [json.loads(line) for line in self.docker_log.read_text().splitlines()]

    def ssh_calls(self) -> list[list[str]]:
        if not self.ssh_log.exists():
            return []
        return [json.loads(line) for line in self.ssh_log.read_text().splitlines()]


def _without_guard(text: str, guard: str) -> str:
    block = re.compile(
        rf"^[ \t]*# >>> guard: {re.escape(guard)}\n.*?^[ \t]*# <<< guard: {re.escape(guard)}\n",
        re.DOTALL | re.MULTILINE,
    )
    mutated, count = block.subn("", text)
    assert count == 1, f"the guard markers for {guard!r} are not a single block"
    return mutated


def _now(offset_seconds: int = 0) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + offset_seconds))


def _record_text(
    *,
    kind: str = "test_data_waiver",
    state: str = "open",
    purpose: str = "import",
    attested: bool = True,
    quiesced_offset: int = -60,
    expires_offset: int = 3600,
    real_data_marker: bool = False,
    target_sha: str | None = None,
) -> str:
    """A copy record in `lib/forced-command.sh`'s canonical layout (`W54-STAND-COPY-01`).
    The default is the record `R-110` makes usual: an open, unexpired test-data waiver."""
    waiver = attestation = None
    if kind == "test_data_waiver" and attested:
        waiver = {"statement": "test data only", "attested_at": _now(-60), "expires_at": _now(expires_offset)}
    if kind == "copy" and attested:
        attestation = {"dump_sha256": "d" * 64, "restore_report_sha256": "c" * 64, "attested_at": _now(-30)}
    fields = {
        "kind": kind, "stamp": "20261012T180000Z", "state": state, "purpose": purpose, "target_sha": target_sha,
        "instance": "an-instance", "deployed_tree": "e" * 40, "migration_head": "0019_execution_workers",
        "opened_at": _now(quiesced_offset), "quiesced_at": _now(quiesced_offset),
        "writers_present": ["web", "api", "worker"], "writers_stopped": ["web", "api", "worker"],
        "dump": None, "fingerprint": {"algorithm": "stand-fingerprint-v1", "sha256": "f" * 64, "tables": {}},
        "rejected_blob_count": 0, "inventory": None, "attestation": attestation, "waiver": waiver,
        "real_data_marker": real_data_marker, "restored_at": None, "closed_at": None,
    }
    lines = ['  "record_version": 1'] + [f'  "{key}": {json.dumps(value)}' for key, value in fields.items()]
    return "{\n" + ",\n".join(lines) + "\n}\n"


def _stage(tmp_path: Path, *, mutant: tuple[str, str] | None = None) -> Stand:
    """`mutant` is (file under infra/deploy, guard name): that block is deleted there."""
    repo = tmp_path / "repo"
    deploy = repo / "infra/deploy"
    (deploy / "lib").mkdir(parents=True)
    for relative, source in SCRIPTS.items():
        text = source.read_text(encoding="utf-8")
        if mutant is not None and mutant[0] == relative:
            text = _without_guard(text, mutant[1])
        target = deploy / relative
        target.write_text(text, encoding="utf-8")
        target.chmod(0o755)
    (deploy / "compose.server.yml").write_text("# stub; docker is a stub\n", encoding="utf-8")
    (deploy / "env").mkdir()
    env_file = deploy / "env/alpha.env"
    env_file.write_text("ALPHA_INSTANCE=an-instance\n", encoding="utf-8")

    staging = tmp_path / "staging"
    staging.mkdir()
    staging.chmod(0o700)
    record = tmp_path / "copy/record.json"
    record.parent.mkdir()
    record.write_text(_record_text(), encoding="utf-8")

    binary = tmp_path / "bin"
    binary.mkdir()
    for name, body in (("docker", DOCKER_STUB), ("ssh", SSH_STUB)):
        (binary / name).write_text(body, encoding="utf-8")
        (binary / name).chmod(0o755)
    return Stand(
        root=tmp_path, deploy=deploy, staging=staging, record=record, env_file=env_file,
        bin=binary, docker_log=tmp_path / "docker.log", ssh_log=tmp_path / "ssh.log",
    )


@dataclass
class Ran:
    completed: subprocess.CompletedProcess[str]
    consumed: int

    @property
    def code(self) -> int:
        return self.completed.returncode

    @property
    def err(self) -> str:
        return self.completed.stderr

    @property
    def out(self) -> str:
        return self.completed.stdout

    def refused(self, guard: str) -> bool:
        return self.code == REFUSED and f"REFUSED [{guard}]" in self.err


def _environment(stand: Stand, extra: dict[str, str | None] | None) -> dict[str, str]:
    environment = dict(os.environ)
    environment.pop("SSH_ORIGINAL_COMMAND", None)
    environment.update(
        PATH=f"{stand.bin}{os.pathsep}{environment['PATH']}",
        BUNDLE_STAGING=str(stand.staging),
        STAND_COPY_RECORD=str(stand.record),
        ALPHA_ENV_FILE=str(stand.env_file),
        BUNDLE_STAGING_MARGIN_BYTES="0",
        STUB_LOG=str(stand.docker_log),
        SSH_LOG=str(stand.ssh_log),
        LC_ALL="C",
    )
    for name, value in (extra or {}).items():
        if value is None:
            environment.pop(name, None)
        else:
            environment[name] = value
    return environment


def _run(
    stand: Stand,
    argv: list[str],
    *,
    stdin: bytes = b"",
    env: dict[str, str | None] | None = None,
) -> Ran:
    feed = stand.root / f"stdin-{time.monotonic_ns()}"
    feed.write_bytes(stdin)
    with feed.open("rb") as handle:
        completed = subprocess.run(
            argv, stdin=handle, capture_output=True, text=True,
            env=_environment(stand, env), cwd=stand.root, timeout=120,
        )
        consumed = os.lseek(handle.fileno(), 0, os.SEEK_CUR)
    return Ran(completed, consumed)


def _inbound(
    stand: Stand,
    command: str | None,
    *,
    stdin: bytes = b"",
    env: dict[str, str | None] | None = None,
) -> Ran:
    """The stand side, as sshd runs a forced command: the client's words in one variable."""
    extra = dict(env or {})
    if command is not None:
        extra["SSH_ORIGINAL_COMMAND"] = command
    return _run(stand, ["bash", str(stand.receive)], stdin=stdin, env=extra)


def _push(stand: Stand, *args: str, env: dict[str, str | None] | None = None) -> Ran:
    return _run(stand, ["bash", str(stand.push), *args], env=env)


# --- bundles --------------------------------------------------------------------------

DEFAULT_FILES = {
    "manifest.json": b'{"version": 1}\n',
    "rows/norm_paragraph.jsonl": b'{"id": "npar_1"}\n',
    "objects/3f/3f9a.pdf": b"%PDF-1.7 not really\n",
}


def _sums(files: dict[str, bytes]) -> bytes:
    return b"".join(
        f"{hashlib.sha256(body).hexdigest()}  {name}\n".encode() for name, body in sorted(files.items())
    )


def _bundle(
    where: Path,
    *,
    content_key: str = REPAIRED_KEY,
    files: dict[str, bytes] | None = None,
    sums: bytes | None = None,
    digest: str | None = None,
    extra: dict[str, bytes] | None = None,
    tamper: dict[str, bytes] | None = None,
) -> Path:
    """A bundle directory named `<content_key>+<sha256(SHA256SUMS)>`.

    `sums` replaces the honest SHA256SUMS; `digest` replaces the honest name digest;
    `extra` adds unlisted files; `tamper` rewrites listed files after they were summed.
    """
    files = dict(DEFAULT_FILES if files is None else files)
    body = _sums(files) if sums is None else sums
    key = f"{content_key}+{digest or hashlib.sha256(body).hexdigest()}"
    bundle = where / key
    for name, data in {**files, **(extra or {}), **(tamper or {})}.items():
        (bundle / name).parent.mkdir(parents=True, exist_ok=True)
        (bundle / name).write_bytes(data)
    bundle.mkdir(parents=True, exist_ok=True)
    (bundle / "SHA256SUMS").write_bytes(body)
    return bundle


def _tar(bundle: Path) -> bytes:
    return subprocess.run(
        ["tar", *TAR_FLAGS, "--directory", str(bundle.parent), "--", bundle.name],
        capture_output=True, check=True,
    ).stdout


def _crafted_tar(members: list[tuple[str, str, bytes | str]]) -> bytes:
    """(name, kind, payload) with kind in file|dir|symlink|hardlink; for links the payload
    is the target. For the members `tar` itself would never write."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.GNU_FORMAT) as archive:
        for name, kind, payload in members:
            info = tarfile.TarInfo(name)
            if kind == "file":
                assert isinstance(payload, bytes)
                info.size = len(payload)
                archive.addfile(info, io.BytesIO(payload))
                continue
            info.type = {"dir": tarfile.DIRTYPE, "symlink": tarfile.SYMTYPE, "hardlink": tarfile.LNKTYPE}[kind]
            if kind == "dir":
                info.mode = 0o755
            else:
                assert isinstance(payload, str)
                info.linkname = payload
            archive.addfile(info)
    return buffer.getvalue()


def _place(stand: Stand, bundle_source: Path) -> str:
    """Put a bundle straight into staging/bundles, as a completed receive leaves it."""
    target = stand.staging / "bundles" / bundle_source.name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(bundle_source, target)
    return bundle_source.name


@contextmanager
def _holding(path: Path) -> Iterator[None]:
    """Hold a flock(2) lock the way another running receive or import would."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


A_KEY = f"{REPAIRED_KEY}+{'a' * 64}"


# --- one case per guard ---------------------------------------------------------------


@dataclass
class Case:
    """Prepares a stand and returns what ran against it."""

    file: str
    run: Callable[[Stand], Ran]
    #: The refusal comes before a byte of stdin is read (receive) / before ssh (push).
    before_read: bool = True
    notes: list[str] = field(default_factory=list)


def _receive_of(bundle_maker: Callable[[Path], Path], *, size_delta: int = 0, raw: bytes | None = None,
                env: dict[str, str | None] | None = None) -> Callable[[Stand], Ran]:
    def run(stand: Stand) -> Ran:
        bundle = bundle_maker(stand.root / "made")
        data = _tar(bundle) if raw is None else raw
        return _inbound(stand, f"receive {bundle.name} {len(data) + size_delta}", stdin=data, env=env)
    return run


def _reported(env: dict[str, str | None] | None = None, *, verb: str = "report",
              prepare: Callable[[Stand], None] | None = None) -> Callable[[Stand], Ran]:
    def run(stand: Stand) -> Ran:
        key = _place(stand, _bundle(stand.root / "made"))
        if prepare is not None:
            prepare(stand)
        return _inbound(stand, f"{verb} {key}", env=env)
    return run


def _declare_writers(stand: Stand) -> None:
    """A compose file that declares the three writers, as the deployed one does."""
    (stand.deploy / "compose.server.yml").write_text(
        "services:\n  postgres:\n    image: x\n  web:\n    image: x\n  api:\n    image: x\n  worker:\n    image: x\n",
        encoding="utf-8",
    )


def _remove_compose(stand: Stand) -> None:
    (stand.deploy / "compose.server.yml").unlink()


def _report_while_locked(stand: Stand) -> Ran:
    key = _place(stand, _bundle(stand.root / "made"))
    with _holding(stand.staging / "import.lock"):
        return _inbound(stand, f"report {key}")


def _receive_while_locked(stand: Stand) -> Ran:
    bundle = _bundle(stand.root / "made")
    data = _tar(bundle)
    with _holding(stand.staging / "receive.lock"):
        return _inbound(stand, f"receive {bundle.name} {len(data)}", stdin=data)


def _receive_again(stand: Stand) -> Ran:
    bundle = _bundle(stand.root / "made")
    _place(stand, bundle)
    data = _tar(bundle)
    return _inbound(stand, f"receive {bundle.name} {len(data)}", stdin=data)


def _symlink_member(stand: Stand) -> Ran:
    bundle = _bundle(stand.root / "made")
    key = bundle.name
    data = _crafted_tar([
        (f"{key}/", "dir", ""),
        (f"{key}/SHA256SUMS", "file", (bundle / "SHA256SUMS").read_bytes()),
        (f"{key}/manifest.json", "symlink", "/etc/hostname"),
    ])
    return _inbound(stand, f"receive {key} {len(data)}", stdin=data)


def _no_sums(where: Path) -> Path:
    bundle = _bundle(where)
    (bundle / "SHA256SUMS").unlink()
    return bundle


def _push_with(*args: str, env: dict[str, str | None] | None = None,
               bundle_name: str | None = None) -> Callable[[Stand], Ran]:
    def run(stand: Stand) -> Ran:
        bundle = _bundle(stand.root / "made")
        if bundle_name is not None:
            bundle = bundle.rename(bundle.parent / bundle_name)
        identity = stand.root / "id_inbound"
        identity.write_text("not a key; ssh is a stub\n")
        full = [a.replace("{identity}", str(identity)).replace("{bundle}", str(bundle)) for a in args]
        return _push(stand, *full, env=env)
    return run


GUARD_CASES: dict[str, Case] = {
    # lib/forced-command.sh -- the dispatcher
    "command-present": Case("lib/forced-command.sh", lambda s: _inbound(s, None)),
    "command-length": Case("lib/forced-command.sh", lambda s: _inbound(s, "status " + "a" * 600)),
    "command-charset": Case("lib/forced-command.sh", lambda s: _inbound(s, "status;touch pwned")),
    "verb-known": Case("lib/forced-command.sh", lambda s: _inbound(s, "shell")),
    "verb-grammar": Case("lib/forced-command.sh", lambda s: _inbound(s, "status now")),
    # lib/forced-command.sh -- the bundle tree rule, here reached through receive
    "sums-present": Case("lib/forced-command.sh", _receive_of(_no_sums), before_read=False),
    "sums-match-key": Case(
        "lib/forced-command.sh", _receive_of(lambda w: _bundle(w, digest="b" * 64)), before_read=False
    ),
    "sums-well-formed": Case(
        "lib/forced-command.sh",
        _receive_of(lambda w: _bundle(w, sums=_sums(DEFAULT_FILES) + b"0" * 64 + b"  ../../outside\n")),
        before_read=False,
    ),
    "files-match-sums": Case(
        "lib/forced-command.sh",
        _receive_of(lambda w: _bundle(w, extra={"unlisted.bin": b"x"})),
        before_read=False,
    ),
    "sums-verify": Case(
        "lib/forced-command.sh",
        _receive_of(lambda w: _bundle(w, tamper={"manifest.json": b'{"version": 2}\n'})),
        before_read=False,
    ),
    # receive-bundle.sh -- configuration every verb shares
    "staging-absolute": Case(
        "receive-bundle.sh", lambda s: _inbound(s, "status", env={"BUNDLE_STAGING": "relative/staging"})
    ),
    "staging-directory": Case(
        "receive-bundle.sh", lambda s: _inbound(s, "status", env={"BUNDLE_STAGING": str(s.root / "absent")})
    ),
    "staging-owned": Case(
        "receive-bundle.sh", lambda s: (s.staging.chmod(0o777), _inbound(s, "status"))[1]
    ),
    "staging-outside-checkout": Case(
        "receive-bundle.sh",
        lambda s: _inbound(s, "status", env={"BUNDLE_STAGING": str(s.deploy / "lib")}),
    ),
    # receive-bundle.sh -- import / report / requeue preconditions
    "bundle-received": Case("receive-bundle.sh", lambda s: _inbound(s, f"report {A_KEY}")),
    "env-file-present": Case(
        "receive-bundle.sh", _reported(env={"ALPHA_ENV_FILE": "/nonexistent/alpha.env"})
    ),
    "compose-file-present": Case("receive-bundle.sh", _reported(prepare=_remove_compose)),
    "copy-record-present": Case(
        "receive-bundle.sh",
        _reported(env={"STAND_COPY_RECORD": "/nonexistent/record.json"}, verb="import"),
    ),
    "import-lock-free": Case("receive-bundle.sh", _report_while_locked),
    # receive-bundle.sh -- the copy record admits the import (`W54-STAND-COPY-01`)
    "copy-record-readable": Case(
        "receive-bundle.sh", _reported(verb="import", prepare=lambda s: s.record.write_text('{"record_version": 1}\n'))
    ),
    "copy-record-open": Case(
        "receive-bundle.sh", _reported(verb="import", prepare=lambda s: s.record.write_text(_record_text(state="closed")))
    ),
    "copy-record-attested": Case(
        "receive-bundle.sh",
        _reported(verb="import", prepare=lambda s: s.record.write_text(_record_text(kind="copy", attested=False))),
    ),
    "waiver-before-real-data": Case(
        "receive-bundle.sh",
        _reported(verb="import", prepare=lambda s: (s.record.parent / "real_data").write_text("stamp=x\n")),
    ),
    "copy-record-in-window": Case(
        "receive-bundle.sh",
        _reported(verb="import", prepare=lambda s: s.record.write_text(_record_text(expires_offset=-1))),
    ),
    "writers-still-stopped": Case(
        "receive-bundle.sh",
        _reported(verb="import", env={"STUB_RUNNING": "worker"}, prepare=lambda s: _declare_writers(s)),
    ),
    # receive-bundle.sh -- receive, before a byte is read
    "size-within-limit": Case(
        "receive-bundle.sh", _receive_of(_bundle, env={"BUNDLE_MAX_BYTES": "1000"})
    ),
    "bundle-not-received": Case("receive-bundle.sh", _receive_again),
    "receive-lock-free": Case("receive-bundle.sh", _receive_while_locked),
    "staging-has-room": Case(
        "receive-bundle.sh",
        _receive_of(_bundle, env={"BUNDLE_STAGING_MARGIN_BYTES": str(10**17)}),
    ),
    # receive-bundle.sh -- receive, after reading
    "tar-length": Case("receive-bundle.sh", _receive_of(_bundle, size_delta=1), before_read=False),
    "tar-readable": Case(
        "receive-bundle.sh", _receive_of(_bundle, raw=b"not a tar archive\n" * 600), before_read=False
    ),
    "tar-members-safe": Case("receive-bundle.sh", _symlink_member, before_read=False),
    # push-bundle.sh -- this side, before ssh
    "known-options": Case("push-bundle.sh", _push_with("--bogus", "{bundle}")),
    "bundle-dir-present": Case("push-bundle.sh", _push_with("--dry-run", "/nonexistent/bundle")),
    "bundle-name-grammar": Case(
        "push-bundle.sh", _push_with("--dry-run", "{bundle}", bundle_name="not-a-bundle-name")
    ),
    "host-configured": Case(
        "push-bundle.sh",
        _push_with("--identity", "{identity}", "{bundle}", env={"STAND_INBOUND_HOST": None}),
    ),
    "identity-present": Case(
        "push-bundle.sh",
        _push_with("--host", "u@stand", "--identity", "/nonexistent/key", "{bundle}"),
    ),
}


def _markers(path: Path) -> list[str]:
    return re.findall(r"^[ \t]*# >>> guard: ([a-z-]+)$", path.read_text(encoding="utf-8"), re.M)


@pytest.mark.parametrize("guard", sorted(GUARD_CASES))
def test_each_guard_refuses_and_its_deletion_stops_the_refusal(tmp_path: Path, guard: str) -> None:
    case = GUARD_CASES[guard]
    assert guard in _markers(DEPLOY / case.file), f"{guard} is not a marked guard in {case.file}"

    stand = _stage(tmp_path / "original")
    ran = case.run(stand)
    assert ran.refused(guard), (guard, ran.code, ran.out, ran.err)
    # `writers-still-stopped` asks compose which writer runs (read-only `ps`); nothing
    # else may reach docker before a refusal.
    assert [call for call in stand.docker_calls() if call[5:6] != ["ps"]] == [], "a refusal reached docker"
    assert stand.ssh_calls() == [], "a refusal reached ssh"
    if case.before_read:
        assert ran.consumed == 0, f"{guard} refused after reading {ran.consumed} bytes"
    incoming = stand.staging / "incoming"
    assert not incoming.exists() or list(incoming.iterdir()) == [], "a refusal left bytes in incoming/"

    mutant = _stage(tmp_path / "mutant", mutant=(case.file, guard))
    unguarded = case.run(mutant)
    assert f"REFUSED [{guard}]" not in unguarded.err, (
        f"deleting the {guard} block did not stop the refusal; something else produces it"
    )


def test_every_guard_has_a_case_here() -> None:
    markers: list[str] = []
    for path in SCRIPTS.values():
        found = _markers(path)
        assert len(found) == len(set(found)), (path, found)
        markers += found
    assert len(markers) == len(set(markers)), "a guard name is used in two files"
    assert set(markers) == set(GUARD_CASES), set(markers) ^ set(GUARD_CASES)
    for guard, case in GUARD_CASES.items():
        assert guard in _markers(DEPLOY / case.file), (guard, case.file)


# --- the grammar of every inbound verb ------------------------------------------------

CK = REPAIRED_KEY
GRAMMAR_VIOLATIONS: dict[str, list[str]] = {
    "receive": [
        "receive",
        f"receive {A_KEY}",
        f"receive {A_KEY} 0",
        f"receive {A_KEY} 012",
        f"receive {A_KEY} -12",
        f"receive {A_KEY} 12 12",
        f"receive {A_KEY}  12",
        f"receive {A_KEY} 1234567890123",
        f"receive {CK} 12",
        "receive not-a-bundle 12",
    ],
    "status": ["status now", "status ", "status status"],
    "import": [
        "import",
        f"import {A_KEY} {A_KEY}",
        f"import {CK}",
        f"import {CK}+{'a' * 63}",
        f"import {CK}+{'A' * 64}",
        f"import {A_KEY} ",
    ],
    "report": [
        "report",
        f"report {A_KEY} --all",
        f"report {CK}+{'a' * 65}",
        f"report 2026-07-23..2026-08-20+17d+0r.4b74348debf7+{'a' * 64}",
    ],
    "requeue": [
        "requeue",
        f"requeue {A_KEY} 1",
        f"requeue {CK.replace('+3u', '+0u')}+{'a' * 64}",
        f"requeue 2026-07-23+17d.4b74348debf7+{'a' * 64}",
    ],
}


def _registered_verbs() -> list[str]:
    return re.findall(r"^fc_register (\S+) ", RECEIVE.read_text(encoding="utf-8"), re.M)


def test_every_verb_has_grammar_violation_cases() -> None:
    verbs = _registered_verbs()
    assert verbs == ["receive", "status", "import", "report", "requeue"], verbs
    assert set(GRAMMAR_VIOLATIONS) == set(verbs), set(GRAMMAR_VIOLATIONS) ^ set(verbs)
    assert all(GRAMMAR_VIOLATIONS[verb] for verb in verbs)


@pytest.mark.parametrize(
    "command",
    [command for verb in GRAMMAR_VIOLATIONS for command in GRAMMAR_VIOLATIONS[verb]],
)
def test_a_grammar_violation_is_refused_before_anything_happens(tmp_path: Path, command: str) -> None:
    stand = _stage(tmp_path)
    ran = _inbound(stand, command, stdin=b"x" * 4096)
    assert ran.refused("verb-grammar"), (command, ran.code, ran.err)
    assert ran.consumed == 0
    assert stand.docker_calls() == []
    assert list(stand.staging.iterdir()) == [], "a refused command wrote to staging"


@pytest.mark.parametrize(
    ("command", "guard"),
    [
        ("status; touch pwned", "command-charset"),
        ("status && touch pwned", "command-charset"),
        ("status $(touch pwned)", "command-charset"),
        ("status `touch pwned`", "command-charset"),
        ("status | touch pwned", "command-charset"),
        ("status\ntouch pwned", "command-charset"),
        ("status\ttouch", "command-charset"),
        (f"report ../{A_KEY}", "command-charset"),
        (f"report {A_KEY}/../../etc", "command-charset"),
        ("report '*'", "command-charset"),
        ("touch pwned", "verb-known"),
        (" status", "verb-known"),
        ("STATUS", "verb-known"),
        ("", "command-present"),
    ],
)
def test_nothing_the_client_sends_is_interpreted(tmp_path: Path, command: str, guard: str) -> None:
    stand = _stage(tmp_path)
    ran = _inbound(stand, command)
    assert ran.refused(guard), (command, ran.err)
    assert not (stand.root / "pwned").exists(), "the command string was executed"
    assert stand.docker_calls() == []


def test_no_script_evaluates_the_client_command() -> None:
    for path in SCRIPTS.values():
        text = path.read_text(encoding="utf-8")
        code = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
        assert not re.search(r"\beval\b", code), f"{path.name} uses eval"
        assert not re.search(r"\bsource\b", code), f"{path.name} sources something besides the lib"
    receive = RECEIVE.read_text(encoding="utf-8")
    uses = [line for line in receive.splitlines()
            if "SSH_ORIGINAL_COMMAND" in line and not line.lstrip().startswith("#")]
    assert uses == ['fc_dispatch "${SSH_ORIGINAL_COMMAND-}"'], uses
    # The one `bash -c` is the import runner, a literal that receives its command as
    # positional parameters.
    assert receive.count("bash -c") == 1
    assert "setsid bash -c 'exit_file=\"$1\"; shift;" in receive


def test_the_scripts_are_strict_and_executable() -> None:
    for path in (RECEIVE, PUSH):
        text = path.read_text(encoding="utf-8")
        assert text.startswith("#!/usr/bin/env bash\n"), path
        assert "\nset -euo pipefail\n" in text, path
        assert os.access(path, os.X_OK), f"{path} is not executable"
        assert '. "$HERE/lib/forced-command.sh"' in text, path
    for path in SCRIPTS.values():
        subprocess.run(["bash", "-n", str(path)], check=True)


def test_shellcheck_finds_nothing() -> None:
    if shutil.which("shellcheck") is None:
        pytest.skip("shellcheck is not installed on this host")
    completed = subprocess.run(
        ["shellcheck", "-x", "infra/deploy/receive-bundle.sh", "infra/deploy/push-bundle.sh",
         "infra/deploy/lib/forced-command.sh"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


# --- the real repaired key ------------------------------------------------------------


def _real_repaired_content_key() -> str:
    """A key minted by the code that mints the corpus keys, not typed here: 30 documents,
    17 undated, the plan's 121 applied repairs and three blocks left degenerate. When
    `W54-REPAIR` makes those three `+3u`, this key changes form and must still pass."""
    from auditmanager.norms import (
        PageRepair,
        RepairOutcome,
        derive,
        fingerprint,
        ledger_of,
        repaired_snapshot,
    )

    documents = [
        fingerprint(
            f"doc_{index:03d}", f"source-{index}", f"text {index}".encode(),
            None if index < 17 else ("2026-07-23" if index % 2 else "2026-08-20"),
        )
        for index in range(30)
    ]
    base = derive(documents)
    repairs = [
        PageRepair(
            document_slug=f"doc_{index % 30:03d}", block_id=f"blk_{index:032x}", page_label=1,
            original_sha256="0" * 64, original_characters=10, crop_sha256="1" * 64,
            outcome=RepairOutcome.REPAIRED if index < 121 else RepairOutcome.STILL_DEGENERATE,
            replacement=f"repaired {index}" if index < 121 else None, attempts=(),
        )
        for index in range(124)
    ]
    key = repaired_snapshot(base, ledger_of(base.snapshot_id, "2026-10-12T00:00:00+00:00", repairs)).content_key
    assert key.startswith("2026-07-23..2026-08-20+17d+121r"), key
    return key


@pytest.mark.parametrize(
    "content_key",
    [
        BASE_KEY,
        "2026-07-23..2026-08-20+17d+121r.4b74348debf7",
        REPAIRED_KEY,
        "2026-07-23..2026-08-20+17d+0r+121u.4b74348debf7",
        "undated+3d.0123456789ab",
        f"{REPAIRED_KEY}+seg-markdown-v2",
        "real-repaired",
    ],
)
def test_a_real_key_is_received_whole(tmp_path: Path, content_key: str) -> None:
    if content_key == "real-repaired":
        content_key = _real_repaired_content_key()
    stand = _stage(tmp_path)
    bundle = _bundle(tmp_path / "made", content_key=content_key)
    data = _tar(bundle)

    ran = _inbound(stand, f"receive {bundle.name} {len(data)}", stdin=data)

    assert ran.code == 0, (ran.out, ran.err)
    assert ran.consumed == len(data)
    received = stand.staging / "bundles" / bundle.name
    for name, body in DEFAULT_FILES.items():
        assert (received / name).read_bytes() == body
    assert list((stand.staging / "incoming").iterdir()) == [], "the work directory was kept"
    assert (stand.staging / "logs" / f"{bundle.name}.received").is_file()
    assert stand.docker_calls() == [], "receive needs no docker"

    status = _inbound(stand, "status")
    assert status.code == 0, status.err
    assert f"bundle: {bundle.name}" in status.out and "import: not imported" in status.out


# --- a mismatching tar is removed, and only inside staging ----------------------------


def _mismatches(stand: Stand) -> dict[str, tuple[str, bytes, str]]:
    """kind -> (KEY, bytes sent, guard) for every way a received tar can be wrong."""
    made = stand.root / "made"
    honest = _bundle(made / "honest")
    honest_tar = _tar(honest)
    key = honest.name
    dotdot = _crafted_tar([
        (f"{key}/SHA256SUMS", "file", (honest / "SHA256SUMS").read_bytes()),
        (f"{key}/../../outside/evil", "file", b"escaped\n"),
    ])
    absolute = _crafted_tar([(str(stand.root / "outside/evil-absolute"), "file", b"escaped\n")])
    hardlink = _crafted_tar([
        (f"{key}/SHA256SUMS", "file", (honest / "SHA256SUMS").read_bytes()),
        (f"{key}/manifest.json", "hardlink", "/etc/hostname"),
    ])
    other_root = _crafted_tar([(f"{key}-other/SHA256SUMS", "file", b"x\n")])
    cases = {
        "short": (key, honest_tar[:-512], "tar-length"),
        "garbage": (key, b"\x00garbage" * 2000, "tar-readable"),
        "dotdot-member": (key, dotdot, "tar-members-safe"),
        "absolute-member": (key, absolute, "tar-members-safe"),
        "hardlink-member": (key, hardlink, "tar-members-safe"),
        "another-root": (key, other_root, "tar-members-safe"),
    }
    for kind, kwargs, guard in (
        ("digest-mismatch", {"digest": "c" * 64}, "sums-match-key"),
        ("tampered-file", {"tamper": {"rows/norm_paragraph.jsonl": b"{}\n"}}, "sums-verify"),
        ("extra-file", {"extra": {"objects/3f/extra.pdf": b"x"}}, "files-match-sums"),
        ("missing-file", {"sums": _sums({**DEFAULT_FILES, "objects/gone.pdf": b"g"})}, "files-match-sums"),
    ):
        bundle = _bundle(made / kind, **kwargs)
        cases[kind] = (bundle.name, _tar(bundle), guard)
    return cases


MISMATCH_KINDS = [
    "short", "garbage", "dotdot-member", "absolute-member", "hardlink-member", "another-root",
    "digest-mismatch", "tampered-file", "extra-file", "missing-file",
]


@pytest.mark.parametrize("kind", MISMATCH_KINDS)
def test_a_mismatching_tar_is_removed_inside_staging_only(tmp_path: Path, kind: str) -> None:
    stand = _stage(tmp_path)
    mismatches = _mismatches(stand)
    assert sorted(mismatches) == sorted(MISMATCH_KINDS)
    key, data, guard = mismatches[kind]

    # What must survive: another received bundle, a file in staging's root, and a file
    # beside staging -- the place an escaping member would land.
    other = _bundle(tmp_path / "other", content_key=BASE_KEY)
    _place(stand, other)
    other_before = {p.relative_to(stand.staging): p.read_bytes()
                    for p in (stand.staging / "bundles").rglob("*") if p.is_file()}
    (stand.staging / "KEEP").write_text("staging sentinel\n")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "KEEP").write_text("outside sentinel\n")

    ran = _inbound(stand, f"receive {key} {len(data) + (512 if kind == 'short' else 0)}", stdin=data)

    assert ran.refused(guard), (kind, ran.code, ran.err)
    assert not (stand.staging / "bundles" / key).exists()
    assert list((stand.staging / "incoming").iterdir()) == [], "the mismatching tar was kept"
    other_after = {p.relative_to(stand.staging): p.read_bytes()
                   for p in (stand.staging / "bundles").rglob("*") if p.is_file()}
    assert other_after == other_before, "a refusal touched another bundle"
    assert (stand.staging / "KEEP").read_text() == "staging sentinel\n"
    assert sorted(p.name for p in outside.iterdir()) == ["KEEP"], "a member escaped staging"
    assert not list(tmp_path.rglob("evil*")), "a member was written somewhere"


def test_bytes_beyond_the_declared_size_are_refused(tmp_path: Path) -> None:
    stand = _stage(tmp_path)
    bundle = _bundle(tmp_path / "made")
    data = _tar(bundle)
    ran = _inbound(stand, f"receive {bundle.name} {len(data)}", stdin=data + b"\x00")
    assert ran.refused("tar-length"), ran.err
    assert "more followed" in ran.err
    assert not (stand.staging / "bundles" / bundle.name).exists()
    assert list((stand.staging / "incoming").iterdir()) == []


def test_the_size_is_refused_before_a_byte_is_read(tmp_path: Path) -> None:
    stand = _stage(tmp_path)
    bundle = _bundle(tmp_path / "made")
    data = _tar(bundle)
    for env, guard in (
        ({"BUNDLE_MAX_BYTES": str(len(data) - 1)}, "size-within-limit"),
        ({"BUNDLE_STAGING_MARGIN_BYTES": str(10**17)}, "staging-has-room"),
    ):
        ran = _inbound(stand, f"receive {bundle.name} {len(data)}", stdin=data, env=env)
        assert ran.refused(guard), ran.err
        assert ran.consumed == 0
        assert "Nothing was read" in ran.err
    # And at the limit itself it is read and kept.
    ran = _inbound(stand, f"receive {bundle.name} {len(data)}", stdin=data,
                   env={"BUNDLE_MAX_BYTES": str(len(data))})
    assert ran.code == 0, ran.err


# --- import / report / requeue run one fixed command ----------------------------------


def _fixed(stand: Stand, action: str, key: str) -> list[str]:
    command = [
        "compose", "--env-file", str(stand.env_file), "--file", str(stand.deploy / "compose.server.yml"),
        "run", "--rm", "--no-deps", "-T", "--entrypoint", "python",
        "--volume", f"{stand.staging}/bundles/{key}:/bundles/{key}:ro",
    ]
    if action in ("import", "report"):
        command += ["--volume", f"{stand.record}:/run/copy-record.json:ro",
                    "api", "-m", "auditmanager.norms.bundle", action, f"/bundles/{key}",
                    "--copy-record", "/run/copy-record.json"]
    else:
        command += ["api", "-m", "auditmanager.norms.bundle", "requeue", f"/bundles/{key}"]
    return command


def _wait_for(path: Path, seconds: float = 20.0) -> None:
    deadline = time.monotonic() + seconds
    while not path.exists():
        assert time.monotonic() < deadline, f"{path} did not appear"
        time.sleep(0.05)


@pytest.mark.parametrize("verb", ["report", "requeue"])
def test_report_and_requeue_run_only_the_fixed_module_command(tmp_path: Path, verb: str) -> None:
    stand = _stage(tmp_path)
    key = _place(stand, _bundle(tmp_path / "made"))
    ran = _inbound(stand, f"{verb} {key}", env={"STUB_EXIT": "0", "STUB_STDOUT": "documents: 563 match"})
    assert ran.code == 0, ran.err
    assert "documents: 563 match" in ran.out
    assert stand.docker_calls() == [_fixed(stand, verb, key)]

    failing = _inbound(stand, f"{verb} {key}", env={"STUB_EXIT": "5"})
    assert failing.code == 5, "the module's exit status is not passed on"
    assert stand.docker_calls()[-1] == _fixed(stand, verb, key)


def test_import_runs_detached_under_the_lock_and_is_re_entrant(tmp_path: Path) -> None:
    stand = _stage(tmp_path)
    key = _place(stand, _bundle(tmp_path / "made"))
    logs = stand.staging / "logs"
    release = tmp_path / "release"

    started = _inbound(stand, f"import {key}", env={"STUB_RELEASE": str(release)})
    assert started.code == 0, started.err
    assert "started (detached" in started.out
    _wait_for(stand.docker_log)
    assert not (logs / f"{key}.import.exit").exists(), "the import did not detach"

    # While it runs: a second import, a report and a requeue are refused in words, and
    # status says the lock is held.
    for verb in ("import", "report", "requeue"):
        assert _inbound(stand, f"{verb} {key}").refused("import-lock-free"), verb
    held = _inbound(stand, "status")
    assert "import_lock: held" in held.out, held.out

    release.write_text("go\n")
    _wait_for(logs / f"{key}.import.exit")
    assert (logs / f"{key}.import.exit").read_text().strip() == "0"
    assert stand.docker_calls() == [_fixed(stand, "import", key)]
    assert "stub module output" in (logs / f"{key}.import.log").read_text()
    deadline = time.monotonic() + 20
    while "import_lock: free" not in _inbound(stand, "status").out:
        assert time.monotonic() < deadline, "the lock outlived the importer"
        time.sleep(0.05)
    assert f"bundle: {key}" in _inbound(stand, "status").out
    assert "import: exited 0" in _inbound(stand, "status").out

    # Re-entrant: a failed run leaves its status, and the next run is accepted.
    failed = _inbound(stand, f"import {key}", env={"STUB_EXIT": "4"})
    assert failed.code == 0, failed.err
    assert not (logs / f"{key}.import.exit").exists(), "a new run kept the last run's status"
    _wait_for(logs / f"{key}.import.exit")
    assert (logs / f"{key}.import.exit").read_text().strip() == "4"
    assert "import: exited 4" in _inbound(stand, "status").out

    deadline = time.monotonic() + 20
    while not (again := _inbound(stand, f"import {key}")).code == 0:
        assert again.refused("import-lock-free"), again.err
        assert time.monotonic() < deadline, "the lock outlived the failed importer"
        time.sleep(0.05)
    _wait_for(logs / f"{key}.import.exit")
    deadline = time.monotonic() + 20
    while (logs / f"{key}.import.exit").read_text().strip() != "0":
        assert time.monotonic() < deadline, "the re-run did not finish"
        time.sleep(0.05)
    calls = stand.docker_calls()
    assert len(calls) == 3
    assert all(call == _fixed(stand, "import", key) for call in calls), calls


# --- the copy record before and during an import (`W54-STAND-COPY-01`) -----------------


def _record(stand: Stand) -> dict:
    return json.loads(stand.record.read_text())


def test_a_receive_makes_an_open_record_an_import_record(tmp_path: Path) -> None:
    stand = _stage(tmp_path)
    stand.record.write_text(_record_text(kind="copy", purpose="publish", target_sha="e" * 40))
    bundle = _bundle(tmp_path / "made")
    data = _tar(bundle)
    ran = _inbound(stand, f"receive {bundle.name} {len(data)}", stdin=data)
    assert ran.code == 0, ran.err
    assert _record(stand)["purpose"] == "import" and _record(stand)["target_sha"] is None
    assert "is now an import record" in ran.err


@pytest.mark.parametrize("state", ["closed", "absent"])
def test_a_receive_leaves_a_closed_record_and_needs_none(tmp_path: Path, state: str) -> None:
    stand = _stage(tmp_path)
    if state == "absent":
        stand.record.unlink()
    else:
        stand.record.write_text(_record_text(kind="copy", state="closed", purpose="publish", target_sha="e" * 40))
    before = stand.record.read_text() if stand.record.exists() else None
    bundle = _bundle(tmp_path / "made")
    data = _tar(bundle)
    ran = _inbound(stand, f"receive {bundle.name} {len(data)}", stdin=data)
    assert ran.code == 0, ran.err
    assert (stand.record.read_text() if stand.record.exists() else None) == before


def test_a_receive_under_an_unreadable_record_is_refused_before_reading(tmp_path: Path) -> None:
    stand = _stage(tmp_path)
    stand.record.write_text("not a record\n")
    bundle = _bundle(tmp_path / "made")
    data = _tar(bundle)
    ran = _inbound(stand, f"receive {bundle.name} {len(data)}", stdin=data)
    assert ran.refused("copy-record-readable"), ran.err
    assert ran.consumed == 0


def test_an_import_under_an_attested_copy_starts_and_makes_it_an_import_record(tmp_path: Path) -> None:
    stand = _stage(tmp_path)
    _declare_writers(stand)
    stand.record.write_text(_record_text(kind="copy", purpose="publish", target_sha="e" * 40))
    key = _place(stand, _bundle(tmp_path / "made"))
    ran = _inbound(stand, f"import {key}")
    assert ran.code == 0, ran.err
    assert _record(stand)["purpose"] == "import"
    _wait_for(stand.staging / "logs" / f"{key}.import.exit")
    asked = [call[-1] for call in stand.docker_calls() if call[5:6] == ["ps"]]
    assert asked == ["web", "api", "worker"], asked


def test_an_attested_copy_older_than_the_window_admits_no_import(tmp_path: Path) -> None:
    stand = _stage(tmp_path)
    stand.record.write_text(_record_text(kind="copy", quiesced_offset=-13 * 3600))
    key = _place(stand, _bundle(tmp_path / "made"))
    ran = _inbound(stand, f"import {key}")
    assert ran.refused("copy-record-in-window"), ran.err
    assert stand.docker_calls() == []


def test_a_waiver_written_after_the_marker_is_refused_even_without_the_file(tmp_path: Path) -> None:
    stand = _stage(tmp_path)
    stand.record.write_text(_record_text(real_data_marker=True))
    key = _place(stand, _bundle(tmp_path / "made"))
    assert _inbound(stand, f"import {key}").refused("waiver-before-real-data")


# --- push-bundle.sh, through the stubbed ssh into the staged receive ------------------


def test_push_bundle_sends_what_receive_keeps(tmp_path: Path) -> None:
    stand = _stage(tmp_path)
    bundle = _bundle(tmp_path / "made")
    identity = tmp_path / "id_inbound"
    identity.write_text("not a key\n")

    ran = _push(stand, "--host", "deploy@stand", "--identity", str(identity),
                "--known-hosts", str(tmp_path / "known_hosts"), str(bundle),
                env={"SSH_FORWARD": str(stand.receive)})

    assert ran.code == 0, (ran.out, ran.err)
    size = len(_tar(bundle))
    [call] = stand.ssh_calls()
    assert call[-2:] == ["deploy@stand", f"receive {bundle.name} {size}"]
    for option in ("BatchMode=yes", "IdentitiesOnly=yes", "StrictHostKeyChecking=yes",
                   f"UserKnownHostsFile={tmp_path / 'known_hosts'}"):
        assert option in call, (option, call)
    assert call[call.index("-i") + 1] == str(identity)
    received = stand.staging / "bundles" / bundle.name
    assert sorted(p.relative_to(received).as_posix() for p in received.rglob("*") if p.is_file()) == sorted(
        [*DEFAULT_FILES, "SHA256SUMS"]
    )


def test_push_bundle_passes_the_stands_refusal_on(tmp_path: Path) -> None:
    stand = _stage(tmp_path)
    bundle = _bundle(tmp_path / "made")
    _place(stand, bundle)
    identity = tmp_path / "id_inbound"
    identity.write_text("not a key\n")
    ran = _push(stand, "--host", "deploy@stand", "--identity", str(identity), str(bundle),
                env={"SSH_FORWARD": str(stand.receive)})
    assert ran.code == REFUSED
    assert "REFUSED [bundle-not-received]" in ran.err
    assert "the stand did not keep" in ran.err


@pytest.mark.parametrize(
    ("kwargs", "guard"),
    [
        ({"digest": "d" * 64}, "sums-match-key"),
        ({"tamper": {"manifest.json": b"changed\n"}}, "sums-verify"),
        ({"extra": {"stray.txt": b"x"}}, "files-match-sums"),
    ],
)
def test_push_bundle_re_hashes_before_anything_leaves(tmp_path: Path, kwargs: dict, guard: str) -> None:
    stand = _stage(tmp_path)
    bundle = _bundle(tmp_path / "made", **kwargs)
    identity = tmp_path / "id_inbound"
    identity.write_text("not a key\n")
    ran = _push(stand, "--host", "deploy@stand", "--identity", str(identity), str(bundle))
    assert ran.refused(guard), ran.err
    assert stand.ssh_calls() == [], "a bundle that fails here was sent"


def test_push_bundle_tars_exactly_as_this_suite_does() -> None:
    text = PUSH.read_text(encoding="utf-8")
    for flag in TAR_FLAGS:
        assert flag.split("=")[0] in text, flag
    assert "--mode='u+rwX,go+rX,go-w'" in text
    assert "--sort=name" in text and "--hard-dereference" in text
