"""`W54-STAND-COPY-01` -- the copy key refuses every guard and every grammar violation, and
what it does when it does not refuse is the one-off copy `W54-PLAN.md` §3.5 and §3.10 name.

Under test: `infra/deploy/copy-serve.sh` (the copy key's forced command on the stand),
`infra/deploy/capacity-probe.sh`, `infra/deploy/pull-copy.sh` and
`scripts/stand-copy/restore-test.sh` (this host), the copy-record helpers in
`infra/deploy/lib/forced-command.sh`, and -- end to end -- what `deploy.sh` and
`receive-bundle.sh` make of the records `copy-serve.sh` writes. `W54-FREEZE-01` amendments 1
and 2 (`R-109`, `R-110`): the test-data waiver and the `real_data` marker.

**The shape of each guard case is `test_bundle_transport_refusals.py`'s.** For every guard
marked `# >>> guard: <name>` in the four scripts: an invocation that trips it exits 3 and
prints `REFUSED [<name>]`, and the same invocation against a copy with exactly that block
deleted does not. A marker without a case, or a case without a marker, reddens
`test_every_guard_has_a_case_here`; a verb without grammar cases reddens
`test_every_verb_has_grammar_violation_cases`.

**Nothing here reaches a daemon, a network or a stand.** `docker` and `ssh` are stubs on
`PATH`. The `docker` stub keeps a small state file -- which services are running, whether a
restore happened -- so `stop`, `start` and `ps` answer one another the way compose does,
and it answers `psql`, `pg_dump`, `pg_restore`, `mc` and the read-back program from values
each case chooses. The `ssh` stub hands its remote command to the staged `copy-serve.sh`, as
sshd does with a forced command. The copy is "installed" apart from the checkout, as the
owner installs it (`DEPLOYMENT_RUNBOOK.md` §13), so every case also shows the script acts on
`ALPHA_CHECKOUT` and not on where it lies.

**What needs a real PostgreSQL** -- a dump restored here reproduces the stand's fingerprint,
and the fingerprint ignores exactly the custody and `norm*` rows -- is
`test_a_dump_restored_here_reproduces_the_fingerprint`, a heavy step that runs only when
`W54_STAND_COPY_WINDOW=1` is set inside an owner-designated window.
"""

from __future__ import annotations

import calendar
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
DEPLOY_DIR = ROOT / "infra/deploy"
COPY_SERVE = DEPLOY_DIR / "copy-serve.sh"
PROBE = DEPLOY_DIR / "capacity-probe.sh"
PULL = DEPLOY_DIR / "pull-copy.sh"
LIB = DEPLOY_DIR / "lib/forced-command.sh"
RESTORE_TEST = ROOT / "scripts/stand-copy/restore-test.sh"
DEPLOY_SH = DEPLOY_DIR / "deploy.sh"
RECEIVE = DEPLOY_DIR / "receive-bundle.sh"
COMPOSE = DEPLOY_DIR / "compose.server.yml"

#: Every script with guards here, by the name its refusals print and its file.
SCRIPTS = {
    "copy-serve.sh": COPY_SERVE,
    "capacity-probe.sh": PROBE,
    "pull-copy.sh": PULL,
    "restore-test.sh": RESTORE_TEST,
}

REFUSED = 3


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


#: The fingerprint query's output on the "stand": one line per table, sorted by name.
FINGERPRINT = "".join(
    f"{table}|{rows}|{_sha(table)}\n"
    for table, rows in (("alembic_version", 1), ("app_user", 2), ("audit_event", 7), ("blob", 3), ("project", 1))
)
OTHER_FINGERPRINT = FINGERPRINT.replace("app_user|2|", "app_user|3|")

DUMP_BYTES = "PGDMP custom-format stand-in\n" * 40

BLOB_A = "blob_" + "A" * 26
BLOB_B = "blob_" + "B" * 26
MC_LINES = "\n".join(
    json.dumps({"status": "success", "type": "file", "lastModified": "2026-10-12T10:00:00Z",
                "size": size, "key": key, "etag": etag, "url": "http://s3:9000/", "storageClass": "STANDARD"},
               separators=(",", ":"))
    for key, size, etag in (("blobs/AA/AA/" + "A" * 26, 120, "e1"), ("blobs/BB/BB/" + "B" * 26, 80, "e2"),
                            ("temporary/tok1", 5, "e3"))
) + "\n"

DOCKER_STUB = r'''#!/usr/bin/env python3
"""A `docker` that records, answers from a state file, and reaches nothing."""
import json
import os
import sys
import time

argv = sys.argv[1:]
with open(os.environ["STUB_LOG"], "a", encoding="utf-8") as handle:
    handle.write(json.dumps(argv) + "\n")
state_path = os.environ["STUB_STATE"]
with open(state_path, encoding="utf-8") as handle:
    state = json.load(handle)


def save():
    with open(state_path, "w", encoding="utf-8") as handle:
        json.dump(state, handle)


def out(text):
    sys.stdout.write(text)
    sys.stdout.flush()


def drain():
    return sys.stdin.buffer.read().decode("utf-8", "replace")


def hold(name):
    """Pause, if the case asked: say so in `entered`, then wait for `release`."""
    spec = state.get(name)
    if not spec:
        return
    with open(spec["entered"], "w", encoding="utf-8") as handle:
        handle.write("entered\n")
    deadline = time.time() + 30
    while not os.path.exists(spec["release"]) and time.time() < deadline:
        time.sleep(0.05)


if argv[:1] == ["compose"]:
    sub, rest = argv[5], argv[6:]
    if sub == "ps":
        if state.get("ps_fails"):
            sys.exit(1)
        service = rest[-1]
        if service in state["running"]:
            out(f"cid-{service}\n")
        sys.exit(0)
    if sub == "stop":
        state["running"] = [s for s in state["running"] if s not in rest or s in state.get("stop_ineffective", [])]
        save()
        sys.exit(0)
    if sub == "start":
        hold("start_hold")
        for service in rest:
            if service not in state.get("start_fails", []) and service not in state["running"]:
                state["running"].append(service)
        save()
        sys.exit(0)
    if sub == "exec":
        service, command = rest[1], rest[2:]
        if service == "postgres" and command[0] == "psql":
            if "--command" in command:
                sql = command[command.index("--command") + 1]
                if "pg_database_size" in sql:
                    out(state.get("db_size", "1000000") + "\n")
                elif "alembic_version" in sql:
                    out(state.get("head", "0019_execution_workers") + "\n")
                elif "state = 'rejected'" in sql:
                    out(state.get("rejected", "0") + "\n")
                elif "ORDER BY md5" in sql:
                    out(state.get("sample", ""))
                elif "DROP SCHEMA" in sql:
                    state["dropped"] = True
                    save()
                sys.exit(0)
            sql = drain()
            if "stand-fingerprint-v1" in sql:
                if state.get("restored") and "fingerprint_after_restore" in state:
                    out(state["fingerprint_after_restore"])
                else:
                    out(state["fingerprint"])
            sys.exit(int(state.get("psql_exit", 0)))
        if service == "postgres" and command[0] == "pg_dump":
            out(state.get("dump_bytes", ""))
            sys.exit(0)
        if service == "postgres" and command[0] == "pg_restore":
            data = drain()
            if "--list" in command:
                sys.exit(int(state.get("restore_list_exit", 0)))
            state["restored"] = True
            state["restored_bytes"] = len(data)
            save()
            sys.exit(int(state.get("restore_exit", 0)))
        if service == "s3" and command[0] == "df":
            out("Filesystem 1024-blocks Used Available Capacity Mounted on\n/dev/vdb 1000 10 900 2% /data\n")
            sys.exit(0)
        if service == "s3" and command[0] == "du":
            out("205\t/data\n")
            sys.exit(0)
        sys.exit(0)
    if sub == "run":
        if "auditmanager.norms.bundle" in rest:
            # The inbound key's importer, started detached by receive-bundle.sh.
            hold("import_hold")
            out("importer stand-in\n")
            sys.exit(0)
        if "s3-init" in rest:
            out(state.get("mc_output", ""))
            sys.exit(int(state.get("mc_exit", 0)))
        if "api" in rest:
            with open(os.environ["STUB_LOG"] + ".verify-input", "w", encoding="utf-8") as handle:
                handle.write(drain())
            out(state.get("verify_output", "verified 0 mismatched 0\n"))
            sys.exit(int(state.get("verify_exit", 0)))
        sys.exit(0)
    sys.exit(0)

if argv[:1] == ["info"]:
    out(state.get("docker_root", "/") + "\n")
    sys.exit(0)
if argv[:2] == ["system", "df"]:
    out("TYPE            TOTAL     ACTIVE    SIZE      RECLAIMABLE\nImages          9         7         6.1GB     1.2GB\n")
    sys.exit(0)
if argv[:2] == ["image", "inspect"]:
    if not state.get("image_exists", True):
        sys.exit(1)
    if "--format" in argv:
        out("sha256:" + "9" * 64 + "\n")
    sys.exit(0)
if argv[:1] == ["run"]:
    state["container"] = argv[argv.index("--name") + 1]
    save()
    out("cid-restore\n")
    sys.exit(0)
if argv[:1] == ["exec"]:
    if "pg_isready" in argv:
        state["ready_calls"] = state.get("ready_calls", 0) + 1
        save()
        sys.exit(0 if state.get("ready", True) else 2)
    if "pg_restore" in argv:
        drain()
        sys.exit(int(state.get("restore_exit", 0)))
    if "psql" in argv:
        drain()
        out(state.get("restored_fingerprint", state["fingerprint"]))
        sys.exit(0)
    sys.exit(0)
if argv[:1] == ["rm"]:
    state["removed"] = argv[-1]
    save()
    sys.exit(0)
sys.exit(0)
'''

SSH_STUB = r'''#!/usr/bin/env python3
"""An `ssh` that records and -- like sshd with a forced command -- hands its remote command
to the staged copy-serve.sh. It opens no socket."""
import json
import os
import subprocess
import sys

with open(os.environ["SSH_LOG"], "a", encoding="utf-8") as handle:
    handle.write(json.dumps(sys.argv[1:]) + "\n")
env = dict(os.environ, SSH_ORIGINAL_COMMAND=sys.argv[-1])
sys.exit(subprocess.run(["bash", os.environ["SSH_FORWARD"]], env=env).returncode)
'''


# --- the stage ------------------------------------------------------------------------


def _without_guard(text: str, guard: str) -> str:
    block = re.compile(
        rf"^[ \t]*# >>> guard: {re.escape(guard)}\n.*?^[ \t]*# <<< guard: {re.escape(guard)}\n",
        re.DOTALL | re.MULTILINE,
    )
    mutated, count = block.subn("", text)
    assert count == 1, f"the guard markers for {guard!r} are not a single block"
    return mutated


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=stand", "-c", "user.email=stand@example.invalid", *args],
        cwd=repo, check=True, capture_output=True, text=True,
    ).stdout.strip()


def _compose_without_worker() -> str:
    lines = COMPOSE.read_text(encoding="utf-8").splitlines(keepends=True)
    start = lines.index("  worker:\n")
    end = start + 1
    while end < len(lines) and not (
        lines[end].startswith("  ") and not lines[end].startswith("   ")
        and lines[end].strip() and not lines[end].lstrip().startswith("#")
    ):
        end += 1
    return "".join(lines[:start] + lines[end:])


ENV_TEXT = (
    "ALPHA_INSTANCE=an-instance\nPOSTGRES_DB=the_db\nPOSTGRES_USER=the_user\n"
    "S3_BUCKET=the-bucket\n"
)


@dataclass
class Stand:
    root: Path
    checkout: Path
    install: Path
    here: Path
    copy: Path
    staging: Path
    bin: Path
    state_file: Path
    docker_log: Path
    ssh_log: Path

    @property
    def record(self) -> Path:
        return self.copy / "record.json"

    @property
    def marker(self) -> Path:
        return self.copy / "real_data"

    @property
    def head(self) -> str:
        return _git(self.checkout, "rev-parse", "HEAD")

    def state(self) -> dict:
        return json.loads(self.state_file.read_text())

    def set_state(self, **values: object) -> None:
        state = self.state()
        state.update(values)
        self.state_file.write_text(json.dumps(state))

    def docker_calls(self) -> list[list[str]]:
        if not self.docker_log.exists():
            return []
        return [json.loads(line) for line in self.docker_log.read_text().splitlines()]

    def compose_calls(self, sub: str) -> list[list[str]]:
        return [call[6:] for call in self.docker_calls() if call[:1] == ["compose"] and call[5] == sub]

    def rec(self) -> dict:
        return json.loads(self.record.read_text())


def _stage(
    tmp_path: Path,
    *,
    mutant: tuple[str, str] | None = None,
    compose_text: str | None = None,
    running: tuple[str, ...] = ("web", "api", "worker"),
) -> Stand:
    """`mutant` is (script name, guard): that block is deleted in the staged copy."""

    def text_of(name: str, source: Path) -> str:
        text = source.read_text(encoding="utf-8")
        if mutant is not None and mutant[0] == name:
            text = _without_guard(text, mutant[1])
        return text

    # The deployed checkout: the real compose file, an environment, a commit.
    checkout = tmp_path / "checkout"
    (checkout / "infra/deploy/env").mkdir(parents=True)
    (checkout / "infra/deploy/compose.server.yml").write_text(
        compose_text if compose_text is not None else COMPOSE.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (checkout / "infra/deploy/env/alpha.env").write_text(ENV_TEXT, encoding="utf-8")
    _git(checkout, "init", "-q")
    _git(checkout, "add", "-A")
    _git(checkout, "commit", "-qm", "the deployed tree")

    # The copy key, installed apart from the checkout (`/srv/auditmanager/copy-serve/`).
    install = tmp_path / "install"
    (install / "lib").mkdir(parents=True)
    for name, source, target in (
        ("copy-serve.sh", COPY_SERVE, install / "copy-serve.sh"),
        ("capacity-probe.sh", PROBE, install / "capacity-probe.sh"),
        ("lib", LIB, install / "lib/forced-command.sh"),
    ):
        target.write_text(text_of(name, source), encoding="utf-8")
        target.chmod(0o755)

    # This host's side, laid out as in the repository.
    here = tmp_path / "here"
    (here / "infra/deploy/lib").mkdir(parents=True)
    (here / "scripts/stand-copy").mkdir(parents=True)
    for name, source, target in (
        ("pull-copy.sh", PULL, here / "infra/deploy/pull-copy.sh"),
        ("copy-serve.sh", COPY_SERVE, here / "infra/deploy/copy-serve.sh"),
        ("capacity-probe.sh", PROBE, here / "infra/deploy/capacity-probe.sh"),
        ("lib", LIB, here / "infra/deploy/lib/forced-command.sh"),
        ("restore-test.sh", RESTORE_TEST, here / "scripts/stand-copy/restore-test.sh"),
    ):
        target.write_text(text_of(name, source), encoding="utf-8")
        target.chmod(0o755)

    copy = tmp_path / "copy"
    copy.mkdir(mode=0o700)
    copy.chmod(0o700)
    staging = tmp_path / "staging"
    staging.mkdir()
    staging.chmod(0o700)

    binary = tmp_path / "bin"
    binary.mkdir()
    for name, body in (("docker", DOCKER_STUB), ("ssh", SSH_STUB)):
        (binary / name).write_text(body, encoding="utf-8")
        (binary / name).chmod(0o755)

    state_file = tmp_path / "docker-state.json"
    state_file.write_text(json.dumps({
        "running": list(running),
        "fingerprint": FINGERPRINT,
        "dump_bytes": DUMP_BYTES,
        "mc_output": MC_LINES,
        "docker_root": str(tmp_path),
    }))
    return Stand(
        root=tmp_path, checkout=checkout, install=install, here=here, copy=copy, staging=staging,
        bin=binary, state_file=state_file, docker_log=tmp_path / "docker.log", ssh_log=tmp_path / "ssh.log",
    )


@dataclass
class Ran:
    completed: subprocess.CompletedProcess[str]

    @property
    def code(self) -> int:
        return self.completed.returncode

    @property
    def out(self) -> str:
        return self.completed.stdout

    @property
    def err(self) -> str:
        return self.completed.stderr

    def refused(self, guard: str) -> bool:
        return self.code == REFUSED and f"REFUSED [{guard}]" in self.err

    def value(self, name: str) -> str:
        match = re.search(rf"^{re.escape(name)}: (\S+)", self.out, re.M)
        assert match, (name, self.out, self.err)
        return match.group(1)


def _environment(stand: Stand, extra: dict[str, str | None] | None) -> dict[str, str]:
    environment = dict(os.environ)
    environment.pop("SSH_ORIGINAL_COMMAND", None)
    environment.update(
        PATH=f"{stand.bin}{os.pathsep}{environment['PATH']}",
        ALPHA_CHECKOUT=str(stand.checkout),
        STAND_COPY_DIR=str(stand.copy),
        BUNDLE_STAGING=str(stand.staging),
        STAND_COPY_MARGIN_BYTES="0",
        STUB_LOG=str(stand.docker_log),
        STUB_STATE=str(stand.state_file),
        SSH_LOG=str(stand.ssh_log),
        SSH_FORWARD=str(stand.install / "copy-serve.sh"),
        STAND_COPY_RESTORE_NEED_RAM="0",
        STAND_COPY_RESTORE_NEED_DISK="0",
        STAND_COPY_RESTORE_READY_SECONDS="2",
        LC_ALL="C",
    )
    environment.pop("ALPHA_ENV_FILE", None)
    for name, value in (extra or {}).items():
        if value is None:
            environment.pop(name, None)
        else:
            environment[name] = value
    return environment


def _copy_key(stand: Stand, command: str | None, *, env: dict[str, str | None] | None = None) -> Ran:
    """The stand side, as sshd runs a forced command."""
    extra = dict(env or {})
    if command is not None:
        extra["SSH_ORIGINAL_COMMAND"] = command
    return Ran(subprocess.run(
        ["bash", str(stand.install / "copy-serve.sh")], capture_output=True, text=True,
        env=_environment(stand, extra), cwd=stand.root, timeout=120, stdin=subprocess.DEVNULL,
    ))


def _here(stand: Stand, script: str, *args: str, env: dict[str, str | None] | None = None) -> Ran:
    path = {
        "pull-copy.sh": stand.here / "infra/deploy/pull-copy.sh",
        "restore-test.sh": stand.here / "scripts/stand-copy/restore-test.sh",
        "capacity-probe.sh": stand.here / "infra/deploy/capacity-probe.sh",
    }[script]
    return Ran(subprocess.run(
        ["bash", str(path), *args], capture_output=True, text=True,
        env=_environment(stand, env), cwd=stand.root, timeout=120, stdin=subprocess.DEVNULL,
    ))


@contextmanager
def _holding(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


# --- steps of the copy, as an operator runs them -------------------------------------


def _dump(stand: Stand) -> str:
    ran = _copy_key(stand, "dump-db")
    assert ran.code == 0, (ran.out, ran.err)
    return ran.value("stamp")


def _inventoried(stand: Stand) -> str:
    stamp = _dump(stand)
    ran = _copy_key(stand, f"inventory-s3 {stamp}")
    assert ran.code == 0, (ran.out, ran.err)
    return stamp


def _dump_sha(stand: Stand) -> str:
    return stand.rec()["dump"]["sha256"]


def _attested(stand: Stand, purpose: str = "import", report: str = "c" * 64) -> str:
    stamp = _inventoried(stand)
    ran = _copy_key(stand, f"attest {stamp} {_dump_sha(stand)} {report} {purpose}")
    assert ran.code == 0, (ran.out, ran.err)
    return stamp


def _waiver(stand: Stand) -> str:
    ran = _copy_key(stand, "attest --test-data")
    assert ran.code == 0, (ran.out, ran.err)
    return ran.value("stamp")


def _resumed(stand: Stand) -> str:
    stamp = _dump(stand)
    ran = _copy_key(stand, f"resume {stamp}")
    assert ran.code == 0, (ran.out, ran.err)
    return stamp


def _set_record(stand: Stand, key: str, value: object) -> None:
    lines = stand.record.read_text().splitlines()
    for index, line in enumerate(lines):
        if line.startswith(f'  "{key}": '):
            comma = "," if line.endswith(",") else ""
            lines[index] = f'  "{key}": {json.dumps(value)}{comma}'
    stand.record.write_text("\n".join(lines) + "\n")


def _pulled(stand: Stand, stamp: str) -> Path:
    identity = stand.root / "id_copy"
    identity.write_text("not a key; ssh is a stub\n")
    dest = stand.root / "pulled"
    dest.mkdir(mode=0o700, exist_ok=True)
    dest.chmod(0o700)
    ran = _here(stand, "pull-copy.sh", "--host", "copy@stand", "--identity", str(identity), stamp, str(dest))
    assert ran.code == 0, (ran.out, ran.err)
    return dest / stamp


A_STAMP = "20200101T000000Z"


# --- one case per guard ---------------------------------------------------------------


@dataclass
class Case:
    run: Callable[[Stand], Ran]
    #: The refusal comes before any `docker` call.
    before_docker: bool = False
    staging: dict | None = None


def _key(command: str, env: dict[str, str | None] | None = None,
         prepare: Callable[[Stand], object] | None = None) -> Callable[[Stand], Ran]:
    def run(stand: Stand) -> Ran:
        prepared = prepare(stand) if prepare is not None else None
        text = command.replace("{stamp}", prepared if isinstance(prepared, str) else A_STAMP)
        if "{dump_sha}" in text:
            text = text.replace("{dump_sha}", _dump_sha(stand))
        return _copy_key(stand, text, env=env)
    return run


def _locked(path_of: Callable[[Stand], Path], command: str,
            prepare: Callable[[Stand], object] | None = None) -> Callable[[Stand], Ran]:
    def run(stand: Stand) -> Ran:
        prepared = prepare(stand) if prepare is not None else None
        with _holding(path_of(stand)):
            return _copy_key(stand, command.replace("{stamp}", prepared if isinstance(prepared, str) else A_STAMP))
    return run


def _garbage_record(stand: Stand) -> None:
    stand.record.write_text('{"record_version": 1, "kind": "copy"}\n')


def _then(*steps: Callable[[Stand], object]) -> Callable[[Stand], object]:
    """Run the steps in order; the first stamp any of them returns is the result."""
    def run(stand: Stand) -> object:
        results = [step(stand) for step in steps]
        return next((result for result in results if isinstance(result, str)), None)
    return run


def _old_quiesce(stand: Stand) -> str:
    stamp = _inventoried(stand)
    _set_record(stand, "quiesced_at", "2020-01-01T00:00:00Z")
    return stamp


def _restarted_writer(stand: Stand) -> str:
    stamp = _dump(stand)
    stand.set_state(running=["web"])
    return stamp


def _pull_case(*, prepare: Callable[[Stand], str] | None = None, args: tuple[str, ...] | None = None,
               env: dict[str, str | None] | None = None, dest_mode: int = 0o700) -> Callable[[Stand], Ran]:
    def run(stand: Stand) -> Ran:
        stamp = prepare(stand) if prepare is not None else A_STAMP
        identity = stand.root / "id_copy"
        identity.write_text("not a key\n")
        dest = stand.root / "pulled"
        dest.mkdir(exist_ok=True)
        dest.chmod(dest_mode)
        argv = args if args is not None else ("--host", "copy@stand", "--identity", str(identity), stamp, str(dest))
        argv = tuple(a.replace("{stamp}", stamp).replace("{dest}", str(dest)).replace("{identity}", str(identity))
                     for a in argv)
        return _here(stand, "pull-copy.sh", *argv, env=env)
    return run


def _tamper_dump(stand: Stand) -> str:
    stamp = _inventoried(stand)
    (stand.copy / stamp / "db.dump").write_text("tampered after the record\n")
    return stamp


def _tamper_inventory(stand: Stand) -> str:
    stamp = _inventoried(stand)
    (stand.copy / stamp / "inventory.tsv").write_text("blobs/x\t1\te\n")
    return stamp


def _restore_case(*, prepare: Callable[[Stand], Path] | None = None, args: tuple[str, ...] | None = None,
                  env: dict[str, str | None] | None = None,
                  state: dict | None = None) -> Callable[[Stand], Ran]:
    def run(stand: Stand) -> Ran:
        if prepare is not None:
            copy = prepare(stand)
        elif args is None:
            copy = _pulled(stand, _inventoried(stand))
        if state:
            stand.set_state(**state)
        argv = args if args is not None else (str(copy),)
        return _here(stand, "restore-test.sh", *argv, env=env)
    return run


def _pulled_then(change: Callable[[Path], None]) -> Callable[[Stand], Path]:
    def run(stand: Stand) -> Path:
        copy = _pulled(stand, _inventoried(stand))
        change(copy)
        return copy
    return run


def _rewrite_record(key: str, value: object) -> Callable[[Path], None]:
    def change(copy: Path) -> None:
        lines = (copy / "record.json").read_text().splitlines()
        lines = [f'  "{key}": {json.dumps(value)},' if line.startswith(f'  "{key}": ') else line for line in lines]
        (copy / "record.json").write_text("\n".join(lines) + "\n")
    return change


def _probe(*args: str) -> Callable[[Stand], Ran]:
    return lambda stand: _here(stand, "capacity-probe.sh", *args)


GUARD_CASES: dict[tuple[str, str], Case] = {
    # copy-serve.sh -- configuration
    ("copy-serve.sh", "checkout-present"): Case(
        _key("dump-db", env={"ALPHA_CHECKOUT": "relative/checkout"}), before_docker=True),
    ("copy-serve.sh", "env-file-present"): Case(
        _key("dump-db", env={"ALPHA_ENV_FILE": "/nonexistent/alpha.env"}), before_docker=True),
    ("copy-serve.sh", "instance-configured"): Case(
        _key("dump-db", prepare=lambda s: (s.checkout / "infra/deploy/env/alpha.env").write_text("ALPHA_INSTANCE=x\n")),
        before_docker=True),
    ("copy-serve.sh", "copy-dir-absolute"): Case(
        _key("dump-db", env={"STAND_COPY_DIR": "relative/copy"}), before_docker=True),
    ("copy-serve.sh", "copy-dir-directory"): Case(
        _key("dump-db", env={"STAND_COPY_DIR": "/nonexistent/copy"}), before_docker=True),
    ("copy-serve.sh", "copy-dir-owned"): Case(
        _key("dump-db", prepare=lambda s: s.copy.chmod(0o777)), before_docker=True),
    ("copy-serve.sh", "copy-dir-outside-checkout"): Case(
        lambda s: (lambda inside: (inside.mkdir(mode=0o700), inside.chmod(0o700),
                                   _copy_key(s, "dump-db", env={"STAND_COPY_DIR": str(inside)}))[2])(
            s.checkout / "copy"),
        before_docker=True),
    # copy-serve.sh -- locks
    ("copy-serve.sh", "copy-lock-free"): Case(_locked(lambda s: s.copy / "copy.lock", "dump-db"), before_docker=True),
    ("copy-serve.sh", "import-lock-free"): Case(
        _locked(lambda s: s.staging / "import.lock", "resume {stamp}", prepare=_dump)),
    # copy-serve.sh -- the record
    ("copy-serve.sh", "record-readable"): Case(
        _key("resume {stamp}", prepare=_garbage_record), before_docker=True),
    ("copy-serve.sh", "record-closed"): Case(_key("dump-db", prepare=_dump)),
    ("copy-serve.sh", "record-open"): Case(_key("resume {stamp}"), before_docker=True),
    ("copy-serve.sh", "record-is-open"): Case(_key("inventory-s3 {stamp}", prepare=_resumed)),
    ("copy-serve.sh", "record-stamp-matches"): Case(
        _key(f"resume {A_STAMP}", prepare=lambda s: (_dump(s), None)[1])),
    ("copy-serve.sh", "record-has-dump"): Case(_key("inventory-s3 {stamp}", prepare=_waiver)),
    # copy-serve.sh -- the stack
    ("copy-serve.sh", "docker-answers"): Case(
        _key("dump-db", prepare=lambda s: s.set_state(ps_fails=True))),
    ("copy-serve.sh", "writers-stopped"): Case(
        _key("dump-db", prepare=lambda s: s.set_state(stop_ineffective=["api"]))),
    ("copy-serve.sh", "writers-still-stopped"): Case(_key("inventory-s3 {stamp}", prepare=_restarted_writer)),
    ("copy-serve.sh", "database-answers"): Case(
        _key("dump-db", prepare=lambda s: s.set_state(db_size="ERROR: relation does not exist"))),
    ("copy-serve.sh", "fingerprint-read"): Case(
        _key("dump-db", prepare=lambda s: s.set_state(fingerprint="not|a|fingerprint\n"))),
    ("copy-serve.sh", "copy-dir-has-room"): Case(
        _key("dump-db", env={"STAND_COPY_MARGIN_BYTES": str(10**17)})),
    ("copy-serve.sh", "dump-readable"): Case(
        _key("dump-db", prepare=lambda s: s.set_state(restore_list_exit=1))),
    ("copy-serve.sh", "inventory-read"): Case(
        _key("inventory-s3 {stamp}", prepare=_then(
            _dump, lambda s: s.set_state(mc_output='{"status":"error","error":{"message":"Access Denied."}}\n')))),
    # copy-serve.sh -- fetch
    ("copy-serve.sh", "fetch-record-present"): Case(_key("fetch {stamp} record"), before_docker=True),
    ("copy-serve.sh", "artifact-present"): Case(_key("fetch {stamp} db", prepare=_waiver)),
    # copy-serve.sh -- attest
    ("copy-serve.sh", "dump-digest-matches"): Case(
        _key(f"attest {{stamp}} {'d' * 64} {'c' * 64} import", prepare=_inventoried)),
    ("copy-serve.sh", "inventory-taken"): Case(
        _key(f"attest {{stamp}} {{dump_sha}} {'c' * 64} import", prepare=_dump)),
    ("copy-serve.sh", "import-record-stays-import"): Case(
        _key(f"attest {{stamp}} {{dump_sha}} {'c' * 64} publish {'f' * 40}", prepare=_attested)),
    ("copy-serve.sh", "window-open"): Case(
        _key(f"attest {{stamp}} {{dump_sha}} {'c' * 64} import", prepare=_old_quiesce)),
    ("copy-serve.sh", "real-data-absent"): Case(
        _key("attest --test-data", prepare=lambda s: s.marker.write_text("stamp=x\n")), before_docker=True),
    # copy-serve.sh -- verify-objects
    ("copy-serve.sh", "sample-read"): Case(
        _key("verify-objects 5", prepare=lambda s: s.set_state(sample="ERROR: no blob table\n"))),
    ("copy-serve.sh", "objects-match"): Case(
        _key("verify-objects 2", prepare=lambda s: s.set_state(
            sample=f"{BLOB_A} 120 {'a' * 64}\n{BLOB_B} 80 {'b' * 64}\n",
            verify_output=f"ok {BLOB_A}\nsha256-mismatch {BLOB_B}\nverified 2 mismatched 1\n", verify_exit=1))),
    # copy-serve.sh -- restore-db and resume
    ("copy-serve.sh", "restore-record-present"): Case(_key(f"restore-db {{stamp}} {'d' * 64}"), before_docker=True),
    ("copy-serve.sh", "dump-digest-matches-restore"): Case(
        _key(f"restore-db {{stamp}} {'d' * 64}", prepare=_resumed)),
    ("copy-serve.sh", "fingerprint-restored"): Case(
        _key("restore-db {stamp} {dump_sha}", prepare=_then(
            _resumed, lambda s: s.set_state(fingerprint_after_restore=OTHER_FINGERPRINT)))),
    ("copy-serve.sh", "writers-resumed"): Case(
        _key("resume {stamp}", prepare=_then(_dump, lambda s: s.set_state(start_fails=["api"])))),
    # capacity-probe.sh
    ("capacity-probe.sh", "known-options"): Case(_probe("--bogus"), before_docker=True),
    ("capacity-probe.sh", "need-measured"): Case(_probe("--need", "nowhere=1"), before_docker=True),
    ("capacity-probe.sh", "disk-has-room"): Case(
        _probe("--path", "root=/", "--need", f"root={10**18}"), before_docker=True),
    ("capacity-probe.sh", "ram-available"): Case(_probe("--need-ram", str(10**18)), before_docker=True),
    # pull-copy.sh
    ("pull-copy.sh", "known-options"): Case(_pull_case(args=("--bogus", A_STAMP, "{dest}")), before_docker=True),
    ("pull-copy.sh", "stamp-grammar"): Case(
        _pull_case(args=("--host", "h", "--identity", "{identity}", "2026-10-12", "{dest}")), before_docker=True),
    ("pull-copy.sh", "host-configured"): Case(
        _pull_case(args=("--identity", "{identity}", A_STAMP, "{dest}"), env={"STAND_COPY_HOST": None}),
        before_docker=True),
    ("pull-copy.sh", "identity-present"): Case(
        _pull_case(args=("--host", "h", "--identity", "/nonexistent/key", A_STAMP, "{dest}")), before_docker=True),
    ("pull-copy.sh", "destination-private"): Case(_pull_case(dest_mode=0o755), before_docker=True),
    ("pull-copy.sh", "copy-not-pulled"): Case(
        _pull_case(prepare=lambda s: ((s.root / "pulled" / A_STAMP).mkdir(parents=True), A_STAMP)[1]),
        before_docker=True),
    ("pull-copy.sh", "record-is-the-copy"): Case(_pull_case(prepare=_dump)),
    ("pull-copy.sh", "dump-matches-record"): Case(_pull_case(prepare=_tamper_dump)),
    ("pull-copy.sh", "inventory-matches-record"): Case(_pull_case(prepare=_tamper_inventory)),
    # restore-test.sh
    ("restore-test.sh", "known-options"): Case(_restore_case(args=("--bogus",)), before_docker=True),
    ("restore-test.sh", "copy-present"): Case(_restore_case(args=("/nonexistent/copy",)), before_docker=True),
    ("restore-test.sh", "record-is-the-copy"): Case(_restore_case(prepare=_pulled_then(_rewrite_record("kind", "other")))),
    ("restore-test.sh", "dump-matches-record"): Case(
        _restore_case(prepare=_pulled_then(lambda c: (c / "db.dump").write_text("changed\n")))),
    ("restore-test.sh", "inventory-matches-record"): Case(
        _restore_case(prepare=_pulled_then(lambda c: (c / "inventory.tsv").write_text("x\t1\te\n")))),
    ("restore-test.sh", "image-present"): Case(_restore_case(state={"image_exists": False})),
    ("restore-test.sh", "host-has-room"): Case(_restore_case(env={"STAND_COPY_RESTORE_NEED_DISK": str(10**18)})),
    ("restore-test.sh", "database-ready"): Case(_restore_case(state={"ready": False})),
    ("restore-test.sh", "dump-restored"): Case(_restore_case(state={"restore_exit": 1})),
    ("restore-test.sh", "fingerprint-read"): Case(_restore_case(state={"restored_fingerprint": "garbage\n"})),
    ("restore-test.sh", "fingerprint-reproduced"): Case(_restore_case(state={"restored_fingerprint": OTHER_FINGERPRINT})),
}


def _markers(path: Path) -> list[str]:
    return re.findall(r"^[ \t]*# >>> guard: ([a-z-]+)$", path.read_text(encoding="utf-8"), re.M)


@pytest.mark.parametrize("key", sorted(GUARD_CASES), ids=lambda k: f"{k[0]}:{k[1]}")
def test_each_guard_refuses_and_its_deletion_stops_the_refusal(tmp_path: Path, key: tuple[str, str]) -> None:
    script, guard = key
    case = GUARD_CASES[key]
    assert guard in _markers(SCRIPTS[script]), f"{guard} is not a marked guard in {script}"

    stand = _stage(tmp_path / "original")
    ran = case.run(stand)
    assert ran.refused(guard), (key, ran.code, ran.out, ran.err)
    assert f"{script}: REFUSED [{guard}]" in ran.err, ran.err
    if case.before_docker:
        assert stand.docker_calls() == [], f"{guard} refused only after calling docker: {stand.docker_calls()}"

    mutant = _stage(tmp_path / "mutant", mutant=key)
    unguarded = case.run(mutant)
    assert f"{script}: REFUSED [{guard}]" not in unguarded.err, (
        f"deleting the {guard} block did not stop the refusal; something else produces it"
    )


def test_every_guard_has_a_case_here() -> None:
    marked: set[tuple[str, str]] = set()
    for name, path in SCRIPTS.items():
        found = _markers(path)
        assert len(found) == len(set(found)), (name, found)
        marked |= {(name, guard) for guard in found}
    assert marked == set(GUARD_CASES), marked ^ set(GUARD_CASES)


# --- the grammar of every copy verb ----------------------------------------------------

S = A_STAMP
D = "d" * 64
GRAMMAR_VIOLATIONS: dict[str, list[str]] = {
    "capacity": ["capacity now", "capacity "],
    "dump-db": ["dump-db now", "dump-db --all"],
    "inventory-s3": ["inventory-s3", f"inventory-s3 {S} {S}", "inventory-s3 2026-10-12", "inventory-s3 20261012T183000"],
    "fetch": ["fetch", f"fetch {S}", f"fetch {S} dump", f"fetch {S} db db", f"fetch {S.lower()} db"],
    "attest": [
        "attest",
        f"attest {S} {D} {D}",
        f"attest {S} {D} {D} publish",
        f"attest {S} {D} {D} publish {'f' * 39}",
        f"attest {S} {D.upper()} {D} import",
        f"attest {S} {D} {D} import now",
        f"attest {S} {D[:63]} {D} import",
        "attest --test-data now",
        "attest --test",
        f"attest --test-data {S}",
    ],
    "verify-objects": [
        "verify-objects", "verify-objects 0", "verify-objects 10000", "verify-objects -1",
        "verify-objects 5 SEED", "verify-objects 5 a b",
    ],
    "restore-db": ["restore-db", f"restore-db {S}", f"restore-db {S} {D[:40]}", f"restore-db {S} {D} now"],
    "resume": ["resume", f"resume {S} {S}", "resume now"],
    "status": ["status now", "status "],
}


def _registered_verbs() -> list[str]:
    return re.findall(r"^fc_register (\S+) ", COPY_SERVE.read_text(encoding="utf-8"), re.M)


def test_every_verb_has_grammar_violation_cases() -> None:
    verbs = _registered_verbs()
    assert verbs == ["capacity", "dump-db", "inventory-s3", "fetch", "attest", "verify-objects",
                     "restore-db", "resume", "status"], verbs
    assert set(GRAMMAR_VIOLATIONS) == set(verbs), set(GRAMMAR_VIOLATIONS) ^ set(verbs)
    assert all(GRAMMAR_VIOLATIONS[verb] for verb in verbs)


@pytest.mark.parametrize("command", [c for verb in GRAMMAR_VIOLATIONS for c in GRAMMAR_VIOLATIONS[verb]])
def test_a_grammar_violation_is_refused_before_anything_happens(tmp_path: Path, command: str) -> None:
    stand = _stage(tmp_path)
    ran = _copy_key(stand, command)
    assert ran.refused("verb-grammar"), (command, ran.code, ran.err)
    assert stand.docker_calls() == []
    assert list(stand.copy.iterdir()) == [], "a refused command wrote to the copy directory"


@pytest.mark.parametrize(
    ("command", "guard"),
    [
        ("status; touch pwned", "command-charset"),
        ("dump-db && touch pwned", "command-charset"),
        ("resume $(touch pwned)", "command-charset"),
        (f"fetch {S} ../record", "command-charset"),
        ("touch pwned", "verb-known"),
        ("receive x 1", "verb-known"),
        ("", "command-present"),
    ],
)
def test_nothing_the_client_sends_is_interpreted(tmp_path: Path, command: str, guard: str) -> None:
    stand = _stage(tmp_path)
    ran = _copy_key(stand, command)
    assert ran.refused(guard), (command, ran.err)
    assert not (stand.root / "pwned").exists()
    assert stand.docker_calls() == []


# --- dump-db stops exactly the writers present -----------------------------------------


@pytest.mark.parametrize(
    ("running", "without_worker", "stopped"),
    [
        (("web", "api", "worker"), False, ["web", "api", "worker"]),
        (("api", "proxy", "postgres"), False, ["api"]),
        ((), False, []),
        # The W53 rollback shape: no worker service is deployed, so a "worker" container
        # that compose would report is not this stack's writer and is not touched.
        (("web", "api", "worker"), True, ["web", "api"]),
    ],
)
def test_dump_db_stops_exactly_the_writers_present(
    tmp_path: Path, running: tuple[str, ...], without_worker: bool, stopped: list[str]
) -> None:
    stand = _stage(tmp_path, running=running,
                   compose_text=_compose_without_worker() if without_worker else None)
    stamp = _dump(stand)

    stops = stand.compose_calls("stop")
    assert stops == ([stopped] if stopped else []), stops
    record = stand.rec()
    assert record["writers_present"] == stopped
    assert record["writers_stopped"] == stopped
    assert record["record_version"] == 1 and record["kind"] == "copy" and record["stamp"] == stamp
    assert record["state"] == "open" and record["purpose"] == "none" and record["target_sha"] is None
    assert record["instance"] == "an-instance"
    assert record["deployed_tree"] == stand.head
    assert record["migration_head"] == "0019_execution_workers"
    assert record["rejected_blob_count"] == 0
    assert record["attestation"] is None and record["waiver"] is None and record["inventory"] is None
    assert record["quiesced_at"] is not None
    dump = stand.copy / stamp / "db.dump"
    assert dump.read_text() == DUMP_BYTES
    assert record["dump"] == {"file": "db.dump", "size_bytes": len(DUMP_BYTES),
                              "sha256": hashlib.sha256(DUMP_BYTES.encode()).hexdigest()}
    assert record["fingerprint"]["algorithm"] == "stand-fingerprint-v1"
    assert record["fingerprint"]["sha256"] == _sha(FINGERPRINT)
    assert record["fingerprint"]["tables"]["app_user"] == {"rows": 2, "sha256": _sha("app_user")}
    assert oct(dump.stat().st_mode & 0o777) == "0o600"
    for service in ("web", "api", "worker"):
        assert (service in stand.state()["running"]) == (service in running and service not in stopped)
    # The pg_dump that wrote it is the plain-format-free, owner-free custom dump.
    [pg_dump] = [c for c in stand.compose_calls("exec") if c[2] == "pg_dump"]
    assert pg_dump == ["-T", "postgres", "pg_dump", "--format=custom", "--no-owner", "--no-privileges",
                       "--username", "the_user", "--dbname", "the_db"]


def test_the_record_is_written_before_anything_stops_so_a_failed_dump_can_resume(tmp_path: Path) -> None:
    stand = _stage(tmp_path)
    stand.set_state(restore_list_exit=1)
    failed = _copy_key(stand, "dump-db")
    assert failed.refused("dump-readable"), failed.err
    record = stand.rec()
    assert record["state"] == "open" and record["dump"] is None
    assert record["writers_stopped"] == ["web", "api", "worker"]
    assert stand.state()["running"] == []
    assert not list((stand.copy / record["stamp"]).glob("db.dump")), "an unreadable dump was kept as the dump"

    resumed = _copy_key(stand, f"resume {record['stamp']}")
    assert resumed.code == 0, resumed.err
    assert sorted(stand.state()["running"]) == ["api", "web", "worker"]
    assert stand.rec()["state"] == "closed" and stand.rec()["closed_at"]


def test_only_the_latest_copy_is_kept(tmp_path: Path) -> None:
    stand = _stage(tmp_path)
    first = _resumed(stand)
    second = _dump(stand)
    assert first != second
    assert not (stand.copy / first).exists()
    assert (stand.copy / second / "db.dump").is_file()
    assert not (stand.copy / "record.prev.json").exists(), "a whole new copy kept the previous record"
    assert _copy_key(stand, f"restore-db {first} {'d' * 64}").refused("record-stamp-matches")


def test_a_failed_dump_keeps_the_previous_copy_restorable(tmp_path: Path) -> None:
    """`W54-JUDGE-A` F6: until a new dump is whole, the previous copy's record stays as
    `record.prev.json`, its dump stays on disk, and `restore-db` takes its stamp -- putting
    that record back, with every writer the failed dump stopped."""
    stand = _stage(tmp_path)
    first = _resumed(stand)
    first_sha = _dump_sha(stand)
    stand.set_state(restore_list_exit=1)
    failed = _copy_key(stand, "dump-db")
    assert failed.refused("dump-readable"), failed.err
    second = stand.rec()["stamp"]
    assert second != first and stand.rec()["state"] == "open" and stand.rec()["dump"] is None
    previous = json.loads((stand.copy / "record.prev.json").read_text())
    assert previous["stamp"] == first and previous["state"] == "closed"
    assert previous["dump"]["sha256"] == first_sha
    assert (stand.copy / first / "db.dump").is_file(), "the previous dump went before the new one was whole"
    assert f"previous_record: {first}" in _copy_key(stand, "status").out
    assert stand.state()["running"] == []

    stand.set_state(restore_list_exit=0)
    assert _copy_key(stand, f"restore-db {A_STAMP} {first_sha}").refused("record-stamp-matches")
    assert _copy_key(stand, f"restore-db {first} {'d' * 64}").refused("dump-digest-matches-restore")
    assert stand.rec()["stamp"] == second, "a refused restore-db moved the records"

    restored = _copy_key(stand, f"restore-db {first} {first_sha}")
    assert restored.code == 0, (restored.out, restored.err)
    assert stand.state()["restored"] and stand.state()["restored_bytes"] == len(DUMP_BYTES)
    record = stand.rec()
    assert record["stamp"] == first and record["state"] == "open" and record["closed_at"] is None
    assert record["restored_at"] and record["writers_stopped"] == ["web", "api", "worker"]
    assert not (stand.copy / "record.prev.json").exists()

    resumed = _copy_key(stand, f"resume {first}")
    assert resumed.code == 0, resumed.err
    assert sorted(stand.state()["running"]) == ["api", "web", "worker"]


def test_a_waiver_replaces_the_record_and_keeps_the_previous_copy(tmp_path: Path) -> None:
    """A waiver has no dump, so the copy before it stays the one `restore-db` can reach --
    through the waiver, and through a dump-db after it that fails."""
    stand = _stage(tmp_path)
    first = _resumed(stand)
    waiver = _waiver(stand)
    assert _copy_key(stand, f"resume {waiver}").code == 0
    assert json.loads((stand.copy / "record.prev.json").read_text())["stamp"] == first
    stand.set_state(restore_list_exit=1)
    assert _copy_key(stand, "dump-db").refused("dump-readable")
    assert json.loads((stand.copy / "record.prev.json").read_text())["stamp"] == first


# --- the whole copy, as P2 runs it (`W54-PLAN.md` §3.10), and what deploy.sh makes of it --


def _deploy_stage(stand: Stand) -> Path:
    """deploy.sh alone in a committed clone: its stand guards run before everything else."""
    repo = stand.root / "deploy-clone"
    (repo / "infra/deploy").mkdir(parents=True)
    (repo / "infra/deploy/deploy.sh").write_text(DEPLOY_SH.read_text(encoding="utf-8"), encoding="utf-8")
    _git(repo, "init", "-q")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "a candidate")
    return repo


def _deploy(stand: Stand, repo: Path) -> Ran:
    before = len(stand.docker_calls())
    ran = Ran(subprocess.run(
        ["bash", str(repo / "infra/deploy/deploy.sh")], capture_output=True, text=True, timeout=60,
        env=_environment(stand, {"STAND_COPY_RECORD": str(stand.record), "ALPHA_ENV_FILE": "/nonexistent/alpha.env"}),
    ))
    assert len(stand.docker_calls()) == before, "deploy.sh called docker"
    return ran


def _deploy_word(ran: Ran) -> str:
    """The typed refusal word, or `passed` when the stand guards let it through to the
    first ordinary guard (this staging has no environment file on purpose)."""
    assert ran.code == REFUSED, (ran.out, ran.err)
    match = re.search(r"REFUSED: \[(stand_[a-z_]+)\]", ran.err)
    if match:
        return match.group(1)
    assert "missing or unreadable" in ran.err, ran.err
    return "passed"


def test_the_whole_copy_binds_both_digests_and_deploy_follows_the_record(tmp_path: Path) -> None:
    stand = _stage(tmp_path)
    clone = _deploy_stage(stand)
    candidate = _git(clone, "rev-parse", "HEAD")
    assert _deploy_word(_deploy(stand, clone)) == "passed", "no record: R-110 needs no copy"

    stamp = _dump(stand)
    assert _deploy_word(_deploy(stand, clone)) == "stand_copy_unattested"
    inventory = _copy_key(stand, f"inventory-s3 {stamp}")
    assert inventory.code == 0, inventory.err
    assert inventory.value("objects") == "3" and inventory.value("bytes") == "205"
    listed = (stand.copy / stamp / "inventory.tsv").read_text().splitlines()
    assert listed == sorted(listed) and listed[0].split("\t") == ["blobs/AA/AA/" + "A" * 26, "120", "e1"]

    pulled = _pulled(stand, stamp)
    assert (pulled / "db.dump").read_text() == DUMP_BYTES
    assert json.loads((pulled / "record.json").read_text())["stamp"] == stamp
    assert [call[-1] for call in json.loads("[" + ",".join(stand.ssh_log.read_text().splitlines()) + "]")] == [
        f"fetch {stamp} record", f"fetch {stamp} db", f"fetch {stamp} inventory"]

    restored = _here(stand, "restore-test.sh", str(pulled))
    assert restored.code == 0, (restored.out, restored.err)
    report = pulled / "restore-report.txt"
    report_sha = hashlib.sha256(report.read_bytes()).hexdigest()
    assert restored.value("report_sha256") == report_sha
    assert f"attest {stamp} {_dump_sha(stand)} {report_sha} publish" in restored.out
    assert stand.state()["removed"].startswith(f"stand-copy-restore-{stamp}-"), "the container was not removed"

    attested = _copy_key(stand, f"attest {stamp} {_dump_sha(stand)} {report_sha} publish {'e' * 40}")
    assert attested.code == 0, attested.err
    record = stand.rec()
    assert record["attestation"]["dump_sha256"] == _dump_sha(stand)
    assert record["attestation"]["restore_report_sha256"] == report_sha
    assert record["purpose"] == "publish" and record["target_sha"] == "e" * 40
    assert record["real_data_marker"] is True and stand.marker.is_file()
    assert _deploy_word(_deploy(stand, clone)) == "stand_copy_other_target"

    # Re-attesting rebinds the publication (a forward fix), and deploy.sh then accepts
    # exactly that commit.
    rebound = _copy_key(stand, f"attest {stamp} {_dump_sha(stand)} {report_sha} publish {candidate}")
    assert rebound.code == 0, rebound.err
    accepted = _deploy(stand, clone)
    assert _deploy_word(accepted) == "passed"
    assert f"under the open copy {stamp}, attested for this commit {candidate}" in accepted.out

    resumed = _copy_key(stand, f"resume {stamp}")
    assert resumed.code == 0, resumed.err
    assert sorted(stand.state()["running"]) == ["api", "web", "worker"]
    assert _deploy_word(_deploy(stand, clone)) == "passed", "a closed record changes nothing"


def test_an_import_record_and_a_waiver_both_stop_deploy(tmp_path: Path) -> None:
    stand = _stage(tmp_path)
    clone = _deploy_stage(stand)
    stamp = _waiver(stand)
    assert _deploy_word(_deploy(stand, clone)) == "stand_import_open"
    assert _copy_key(stand, f"resume {stamp}").code == 0

    stamp = _attested(stand, "import")
    assert _deploy_word(_deploy(stand, clone)) == "stand_import_open"
    with _holding(stand.staging / "import.lock"):
        assert _deploy_word(_deploy(stand, clone)) == "stand_import_locked"
    stand.record.write_text("{}\n")
    assert _deploy_word(_deploy(stand, clone)) == "stand_copy_unreadable"


# --- resume, restore-db --------------------------------------------------------------


def test_resume_is_refused_under_the_import_lock_and_the_writers_stay_stopped(tmp_path: Path) -> None:
    stand = _stage(tmp_path)
    stamp = _attested(stand, "import")
    with _holding(stand.staging / "import.lock"):
        ran = _copy_key(stand, f"resume {stamp}")
    assert ran.refused("import-lock-free"), ran.err
    assert stand.compose_calls("start") == []
    assert stand.state()["running"] == [] and stand.rec()["state"] == "open"
    status = _copy_key(stand, "status")
    assert status.code == 0 and "import_lock: free" in status.out
    assert _copy_key(stand, f"resume {stamp}").code == 0


#: A bundle name the inbound key's grammar admits (`lib/forced-command.sh`).
BUNDLE_KEY = "2026-07-23..2026-08-20+17d.4b74348debf7+" + "a" * 64


def _inbound_key(stand: Stand, command: str) -> Ran:
    """The real `receive-bundle.sh`, in the deployed checkout as deploy-auto leaves it, on
    the same copy record and staging as the copy key."""
    deploy = stand.checkout / "infra/deploy"
    script = deploy / "receive-bundle.sh"
    if not script.exists():
        (deploy / "lib").mkdir(exist_ok=True)
        script.write_text(RECEIVE.read_text(encoding="utf-8"), encoding="utf-8")
        (deploy / "lib/forced-command.sh").write_text(LIB.read_text(encoding="utf-8"), encoding="utf-8")
    return Ran(subprocess.run(
        ["bash", str(script)], capture_output=True, text=True, cwd=stand.root, timeout=120,
        stdin=subprocess.DEVNULL,
        env=_environment(stand, {"SSH_ORIGINAL_COMMAND": command, "STAND_COPY_RECORD": str(stand.record)}),
    ))


def _received_bundle(stand: Stand) -> str:
    """A bundle as a completed receive leaves it; `import` does not re-check the tree."""
    bundle = stand.staging / "bundles" / BUNDLE_KEY
    bundle.mkdir(parents=True)
    (bundle / "SHA256SUMS").write_text("")
    return BUNDLE_KEY


def _wait_for(path: Path, seconds: float = 30.0) -> None:
    deadline = time.monotonic() + seconds
    while not path.exists():
        assert time.monotonic() < deadline, f"{path} did not appear"
        time.sleep(0.05)


def _importer_runs(stand: Stand) -> list[list[str]]:
    return [call for call in stand.docker_calls() if "auditmanager.norms.bundle" in call]


@pytest.mark.parametrize("mutant", [None, ("copy-serve.sh", "import-lock-free")], ids=["as-shipped", "without-the-hold"])
def test_no_import_starts_while_resume_starts_the_writers(tmp_path: Path, mutant: tuple[str, str] | None) -> None:
    """`W54-JUDGE-A` F3: `resume` HOLDS the importer's lock while it starts the writers and
    closes the record, so an import that arrives meanwhile is refused in words -- and so is
    a receive, which needs `copy.lock` (F4). Without the hold (the mutant), the import is
    still refused: `copy.lock`, which resume holds and import takes, closes the same race
    a second time -- but no longer by `import-lock-free`."""
    stand = _stage(tmp_path, mutant=mutant)
    stamp = _waiver(stand)
    key = _received_bundle(stand)
    entered, release = tmp_path / "start-entered", tmp_path / "start-release"
    stand.set_state(start_hold={"entered": str(entered), "release": str(release)})
    resume = subprocess.Popen(
        ["bash", str(stand.install / "copy-serve.sh")], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, cwd=stand.root, stdin=subprocess.DEVNULL,
        env=_environment(stand, {"SSH_ORIGINAL_COMMAND": f"resume {stamp}"}),
    )
    try:
        _wait_for(entered)
        imported = _inbound_key(stand, f"import {key}")
        received = _inbound_key(stand, f"receive {key.replace('a' * 64, 'b' * 64)} 10")
    finally:
        release.write_text("go\n")
        _, resume_err = resume.communicate(timeout=60)
    assert resume.returncode == 0, resume_err
    assert stand.rec()["state"] == "closed"
    assert _importer_runs(stand) == [], "an import started while resume started the writers"
    assert received.refused("copy-lock-free"), received.err
    if mutant is None:
        assert imported.refused("import-lock-free"), imported.err
    else:
        assert imported.refused("copy-lock-free"), imported.err


def test_resume_is_refused_while_the_importer_runs_and_succeeds_after(tmp_path: Path) -> None:
    """The other direction, with the real inbound key: its detached importer holds
    `import.lock` until it exits, and `resume` is refused until then."""
    stand = _stage(tmp_path)
    stamp = _waiver(stand)
    key = _received_bundle(stand)
    entered, release = tmp_path / "import-entered", tmp_path / "import-release"
    stand.set_state(import_hold={"entered": str(entered), "release": str(release)})
    started = _inbound_key(stand, f"import {key}")
    assert started.code == 0, started.err
    try:
        _wait_for(entered)
        refused = _copy_key(stand, f"resume {stamp}")
    finally:
        release.write_text("go\n")
    assert refused.refused("import-lock-free"), refused.err
    assert stand.compose_calls("start") == [] and stand.state()["running"] == []
    assert stand.rec()["state"] == "open"

    _wait_for(stand.staging / "logs" / f"{key}.import.exit")
    deadline = time.monotonic() + 30
    while not (resumed := _copy_key(stand, f"resume {stamp}")).code == 0:
        assert resumed.refused("import-lock-free"), resumed.err
        assert time.monotonic() < deadline, "the import lock outlived the importer"
        time.sleep(0.05)
    assert sorted(stand.state()["running"]) == ["api", "web", "worker"]
    assert stand.rec()["state"] == "closed"


def test_restore_db_quiesces_again_checks_the_digest_and_leaves_the_writers_stopped(tmp_path: Path) -> None:
    stand = _stage(tmp_path, running=("web", "api"))
    stamp = _resumed(stand)
    # A deploy since the copy brought a worker that was not there before.
    stand.set_state(running=["web", "api", "worker"])
    calls = len(stand.docker_calls())

    wrong = _copy_key(stand, f"restore-db {stamp} {'d' * 64}")
    assert wrong.refused("dump-digest-matches-restore")
    assert [c for c in stand.docker_calls()[calls:] if c[:1] == ["compose"] and c[5] in ("stop", "exec")] == [], (
        "a wrong digest stopped or restored something"
    )

    ran = _copy_key(stand, f"restore-db {stamp} {_dump_sha(stand)}")
    assert ran.code == 0, (ran.out, ran.err)
    assert stand.compose_calls("stop")[-1] == ["web", "api", "worker"]
    assert stand.state()["running"] == [] and stand.state()["dropped"] and stand.state()["restored"]
    assert stand.state()["restored_bytes"] == len(DUMP_BYTES)
    record = stand.rec()
    assert record["state"] == "open" and record["closed_at"] is None and record["restored_at"]
    assert record["writers_stopped"] == ["web", "api", "worker"]
    [restore] = [c for c in stand.compose_calls("exec") if c[2] == "pg_restore" and "--list" not in c]
    assert "--exit-on-error" in restore and "--single-transaction" in restore

    # And a dump changed on disk since its record is refused, even with the recorded digest.
    (stand.copy / stamp / "db.dump").write_text("changed\n")
    assert _copy_key(stand, f"restore-db {stamp} {_dump_sha(stand)}").refused("dump-digest-matches-restore")

    assert _copy_key(stand, f"resume {stamp}").code == 0
    assert sorted(stand.state()["running"]) == ["api", "web", "worker"]


def test_resume_starts_only_what_the_deployed_file_still_declares(tmp_path: Path) -> None:
    stand = _stage(tmp_path)
    stamp = _dump(stand)
    (stand.checkout / "infra/deploy/compose.server.yml").write_text(_compose_without_worker())
    ran = _copy_key(stand, f"resume {stamp}")
    assert ran.code == 0, ran.err
    assert stand.compose_calls("start") == [["web", "api"]]
    assert "not in the deployed compose file any more: worker" in ran.out


# --- the waiver and the real_data marker (`W54-FREEZE-01` amendment 2) ----------------


def test_the_test_data_waiver_is_a_quiesced_import_record_without_a_copy(tmp_path: Path) -> None:
    stand = _stage(tmp_path, running=("api", "worker"))
    stamp = _waiver(stand)
    record = stand.rec()
    assert record["kind"] == "test_data_waiver" and record["stamp"] == stamp
    assert record["state"] == "open" and record["purpose"] == "import"
    assert record["dump"] is None and record["inventory"] is None and record["attestation"] is None
    assert record["writers_stopped"] == ["api", "worker"] and stand.state()["running"] == []
    assert record["fingerprint"]["sha256"] == _sha(FINGERPRINT)
    assert record["real_data_marker"] is False and not stand.marker.exists()
    waiver = record["waiver"]
    assert "R-109" in waiver["statement"]
    attested = calendar.timegm(time.strptime(waiver["attested_at"], "%Y-%m-%dT%H:%M:%SZ"))
    expires = calendar.timegm(time.strptime(waiver["expires_at"], "%Y-%m-%dT%H:%M:%SZ"))
    assert expires - attested == 43200
    assert not (stand.copy / stamp).exists(), "a waiver writes no copy directory"


def test_a_full_copy_writes_the_marker_and_every_waiver_is_refused_after_it(tmp_path: Path) -> None:
    stand = _stage(tmp_path)
    assert _copy_key(stand, f"resume {_waiver(stand)}").code == 0, "a waiver before the marker is accepted"
    stamp = _attested(stand, "import")
    assert stand.marker.read_text().startswith(f"stamp={stamp}\n")
    assert _copy_key(stand, f"resume {stamp}").code == 0
    refused = _copy_key(stand, "attest --test-data")
    assert refused.refused("real-data-absent"), refused.err
    assert stand.rec()["kind"] == "copy", "the refused waiver replaced the record"
    status = _copy_key(stand, "status")
    assert "real_data_marker: present" in status.out


def test_a_waiver_is_not_attested_as_a_copy(tmp_path: Path) -> None:
    stand = _stage(tmp_path)
    stamp = _waiver(stand)
    ran = _copy_key(stand, f"attest {stamp} {'d' * 64} {'c' * 64} import")
    assert ran.refused("record-has-dump"), ran.err
    assert not stand.marker.exists()


# --- verify-objects ------------------------------------------------------------------


def _program() -> str:
    text = COPY_SERVE.read_text(encoding="utf-8")
    start = text.index("# >>> verify-objects.py\n")
    end = text.index("# <<< verify-objects.py\n") + len("# <<< verify-objects.py\n")
    return text[start:end]


def _fake_storage(where: Path, objects: dict[str, bytes]) -> dict[str, str]:
    package = where / "fake/auditmanager/storage"
    package.mkdir(parents=True)
    (where / "fake/auditmanager/__init__.py").write_text("")
    (package / "__init__.py").write_text(
        "import json, os\n"
        "BlobId = str\n"
        "class S3StorageSettings:\n"
        "    @classmethod\n"
        "    def from_env(cls):\n"
        "        return cls()\n"
        "class S3BlobStore:\n"
        "    def __init__(self, settings):\n"
        "        self.objects = json.load(open(os.environ['FAKE_OBJECTS']))\n"
        "    def read(self, blob_id, verify=True):\n"
        "        assert verify is False, 'the program hashes the bytes itself'\n"
        "        return self.objects[blob_id].encode('latin-1')\n"
    )
    store = where / "objects.json"
    store.write_text(json.dumps({key: value.decode("latin-1") for key, value in objects.items()}))
    return {"PYTHONPATH": str(where / "fake"), "FAKE_OBJECTS": str(store)}


def test_the_read_back_program_detects_a_corrupted_object(tmp_path: Path) -> None:
    good, bad, short = b"good bytes", b"corrupted!", b"short"
    sample = "".join(
        f"{blob} {size} {hashlib.sha256(body).hexdigest()}\n"
        for blob, size, body in (
            (BLOB_A, len(good), good),
            (BLOB_B, len(bad), b"the bytes recorded"[: len(bad)]),
            ("blob_" + "C" * 26, 99, short),
            ("blob_" + "D" * 26, 3, b"abc"),
        )
    )
    env = dict(os.environ, **_fake_storage(tmp_path, {BLOB_A: good, BLOB_B: bad, "blob_" + "C" * 26: short}))
    ran = subprocess.run([sys.executable, "-c", _program()], input=sample, capture_output=True, text=True, env=env)
    assert ran.returncode == 1, ran.stderr
    assert ran.stdout.splitlines() == [
        f"ok {BLOB_A}",
        f"sha256-mismatch {BLOB_B}",
        f"size-mismatch blob_{'C' * 26} recorded 99 read 5",
        f"unreadable blob_{'D' * 26} KeyError",
        "verified 4 mismatched 3",
    ]

    clean = subprocess.run([sys.executable, "-c", _program()], input=sample.splitlines(True)[0],
                           capture_output=True, text=True, env=env)
    assert clean.returncode == 0 and clean.stdout.endswith("verified 1 mismatched 0\n")
    empty = subprocess.run([sys.executable, "-c", _program()], input="", capture_output=True, text=True, env=env)
    assert empty.returncode == 1, "a sample of nothing verified nothing"


def test_verify_objects_reads_back_the_seeded_sample_through_the_api_image(tmp_path: Path) -> None:
    stand = _stage(tmp_path)
    sample = f"{BLOB_A} 120 {'a' * 64}\n{BLOB_B} 80 {'b' * 64}\n"
    stand.set_state(sample=sample, verify_output=f"ok {BLOB_A}\nok {BLOB_B}\nverified 2 mismatched 0\n")
    ran = _copy_key(stand, "verify-objects 2 w54p2")
    assert ran.code == 0, ran.err
    assert ran.value("seed") == "w54p2" and ran.value("sampled") == "2"
    [query] = [c for c in stand.compose_calls("exec") if c[2] == "psql"]
    assert "ORDER BY md5(blob_id || 'w54p2'), blob_id LIMIT 2" in query[query.index("--command") + 1]
    [run] = stand.compose_calls("run")
    assert run[:6] == ["--rm", "--no-deps", "-T", "--entrypoint", "python", "api"]
    assert run[6] == "-c" and run[7].startswith("# >>> verify-objects.py")
    assert Path(str(stand.docker_log) + ".verify-input").read_text() == sample


# --- capacity, status, and the script installed apart from the checkout ---------------


def test_capacity_prints_every_field(tmp_path: Path) -> None:
    stand = _stage(tmp_path)
    ran = _copy_key(stand, "capacity")
    assert ran.code == 0, (ran.out, ran.err)
    for label in ("docker_root", "staging", "copy_dir"):
        assert re.search(rf"^path {label}: \S+ filesystem=\S+ mount=\S+ avail_bytes=\d+ size_bytes=\d+$", ran.out, re.M), (
            label, ran.out)
    for field_name in ("ram_available_bytes", "swap_total_bytes", "swap_free_bytes", "pg_database_size_bytes",
                       "minio_volume_avail_bytes", "minio_volume_bytes", "bucket_objects", "bucket_bytes"):
        assert re.search(rf"^{field_name}: \d+$", ran.out, re.M), (field_name, ran.out)
    assert re.search(r"^load: [\d.]+ [\d.]+ [\d.]+$", ran.out, re.M)
    assert ran.value("minio_volume_avail_bytes") == str(900 * 1024)
    assert ran.value("bucket_objects") == "3" and ran.value("bucket_bytes") == "205"
    assert "docker_system_df:\n  TYPE" in ran.out
    assert "staging >= bundle + dump + 2 GiB" in ran.out
    assert stand.compose_calls("stop") == [], "capacity stopped something"


def test_the_extracted_script_acts_on_alpha_checkout(tmp_path: Path) -> None:
    stand = _stage(tmp_path)
    assert not str(stand.install).startswith(str(stand.checkout))
    _dump(stand)
    compose_files = {call[4] for call in stand.docker_calls() if call[:1] == ["compose"]}
    env_files = {call[2] for call in stand.docker_calls() if call[:1] == ["compose"]}
    assert compose_files == {str(stand.checkout / "infra/deploy/compose.server.yml")}
    assert env_files == {str(stand.checkout / "infra/deploy/env/alpha.env")}
    assert stand.rec()["deployed_tree"] == stand.head

    status = _copy_key(stand, "status")
    assert status.code == 0
    installed = hashlib.sha256((stand.install / "copy-serve.sh").read_bytes()).hexdigest()
    assert f"script: {installed}" in status.out
    assert f"deployed_tree: {stand.head}" in status.out
    assert "kind: copy  state: open  purpose: none" in status.out


def test_status_reads_without_refusing(tmp_path: Path) -> None:
    stand = _stage(tmp_path)
    assert "record: none" in _copy_key(stand, "status").out
    stand.record.write_text("not json\n")
    assert "record: unreadable" in _copy_key(stand, "status").out
    assert stand.docker_calls() == []


# --- pull-copy removes what does not match ---------------------------------------------


def test_a_pulled_dump_that_does_not_match_is_removed(tmp_path: Path) -> None:
    stand = _stage(tmp_path)
    ran = _pull_case(prepare=_tamper_dump)(stand)
    assert ran.refused("dump-matches-record"), ran.err
    assert list((stand.root / "pulled").iterdir()) == [], "a dump that did not match was left behind"


def test_a_stand_refusal_is_passed_on_by_pull_copy(tmp_path: Path) -> None:
    stand = _stage(tmp_path)
    ran = _pull_case()(stand)
    assert ran.code == REFUSED and "copy-serve.sh: REFUSED [fetch-record-present]" in ran.err
    assert list((stand.root / "pulled").iterdir()) == []


# --- the record helpers in lib/forced-command.sh ---------------------------------------


def _lib(script: str, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["bash", "-c", f'set -euo pipefail; . "{LIB}"; {script}'],
                          capture_output=True, text=True, cwd=tmp_path)


def test_the_record_layout_is_read_and_rewritten_line_by_line(tmp_path: Path) -> None:
    stand = _stage(tmp_path)
    _dump(stand)
    record = stand.record
    before = record.read_text().splitlines()
    ran = _lib(f'fc_take_record_lock "{record}" && fc_record_valid "{record}" && fc_record_set "{record}" purpose \'"import"\' '
               f'&& fc_record_set "{record}" closed_at \'"2026-10-12T00:00:00Z"\' '
               f'&& fc_record_string "{record}" purpose && fc_json_member "$(fc_record_value "{record}" dump)" size_bytes',
               tmp_path)
    assert ran.returncode == 0, ran.stderr
    assert ran.stdout.splitlines() == ["import", str(len(DUMP_BYTES))]
    after = record.read_text().splitlines()
    assert len(after) == len(before) and after[-2] == '  "closed_at": "2026-10-12T00:00:00Z"'
    assert json.loads(record.read_text())["purpose"] == "import"
    assert _lib(f'fc_take_record_lock "{record}" && fc_record_set "{record}" no_such_key 1', tmp_path).returncode != 0


def test_the_record_is_rewritten_only_under_the_copy_lock_beside_it(tmp_path: Path) -> None:
    """`W54-JUDGE-A` F4: one lock for every writer. A rewrite without `copy.lock` -- or
    under the lock of another directory -- fails and changes nothing, and the lock is not
    taken while another process holds it."""
    stand = _stage(tmp_path)
    _dump(stand)
    record = stand.record
    before = record.read_text()
    rewrite = f'fc_record_set "{record}" purpose \'"import"\''

    assert _lib(rewrite, tmp_path).returncode != 0, "a rewrite without copy.lock went through"
    elsewhere = tmp_path / "elsewhere" / "record.json"
    elsewhere.parent.mkdir()
    assert _lib(f'fc_take_record_lock "{elsewhere}" && {rewrite}', tmp_path).returncode != 0, (
        "the lock of another directory admitted the rewrite"
    )
    with _holding(stand.copy / "copy.lock"):
        assert _lib(f'fc_take_record_lock "{record}"', tmp_path).returncode != 0, "a held lock was taken"
    assert record.read_text() == before
    assert not list(stand.copy.glob("record.json.tmp.*")), "a refused rewrite left its temporary file"

    assert _lib(f'fc_take_record_lock "{record}" && {rewrite}', tmp_path).returncode == 0
    assert stand.rec()["purpose"] == "import"


@pytest.mark.parametrize(
    "mangle",
    [
        lambda t: t.replace("{\n", "{ \n", 1),
        lambda t: t.replace('"record_version": 1', '"record_version": 2'),
        lambda t: t.replace('"kind": "copy"', '"kind": "backup"'),
        lambda t: t.replace('"state": "open"', '"state": "maybe"'),
        lambda t: t.replace('  "closed_at": null\n}', '  "closed_at": null,\n}'),
        lambda t: t.replace('"instance": "an-instance"', '"instance": "an\\\\instance"'),
        lambda t: t.replace('  "kind"', '    "kind"'),
        lambda t: json.dumps(json.loads(t)),
    ],
    ids=["brace", "version", "kind", "state", "comma", "backslash", "indent", "one-line-json"],
)
def test_a_record_out_of_layout_is_not_a_record(tmp_path: Path, mangle: Callable[[str], str]) -> None:
    stand = _stage(tmp_path)
    _dump(stand)
    assert _lib(f'fc_record_valid "{stand.record}"', tmp_path).returncode == 0
    stand.record.write_text(mangle(stand.record.read_text()))
    assert _lib(f'fc_record_valid "{stand.record}"', tmp_path).returncode != 0


# --- the scripts themselves ------------------------------------------------------------


def test_the_fingerprint_query_has_one_source() -> None:
    restore = RESTORE_TEST.read_text(encoding="utf-8")
    assert "string_agg" not in restore and "relkind" not in restore, "restore-test.sh carries its own query"
    assert "sed -n '/^-- >>> stand-fingerprint-v1$/,/^-- <<< stand-fingerprint-v1$/p' \"$COPY_SERVE\"" in restore
    serve = COPY_SERVE.read_text(encoding="utf-8")
    query = serve[serve.index("-- >>> stand-fingerprint-v1\n"):serve.index("-- <<< stand-fingerprint-v1\n")]
    for clause in ("NOT LIKE 'norm%'", "norm\\_custody.%", "norm_custody_admission", "\\gexec",
                   "SET TimeZone = 'UTC'", "COLLATE \"C\"", "REPEATABLE READ READ ONLY"):
        assert clause in query, clause


def test_the_scripts_are_strict_executable_and_never_evaluate_the_client() -> None:
    for path in (COPY_SERVE, PROBE, PULL, RESTORE_TEST):
        text = path.read_text(encoding="utf-8")
        assert text.startswith("#!/usr/bin/env bash\n"), path
        assert "\nset -euo pipefail\n" in text, path
        assert os.access(path, os.X_OK), f"{path} is not executable"
        subprocess.run(["bash", "-n", str(path)], check=True)
        code = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
        assert not re.search(r"\beval\b", code), f"{path.name} uses eval"
        assert not re.search(r"(^|[;&|]\s*)\s*source\s", code, re.M), f"{path.name} sources something"
        assert re.findall(r"^\. .*$", code, re.M) in ([], ['. "$HERE/lib/forced-command.sh"'],
                                                     ['. "$REPO/infra/deploy/lib/forced-command.sh"']), path
    serve = COPY_SERVE.read_text(encoding="utf-8")
    uses = [line for line in serve.splitlines() if "SSH_ORIGINAL_COMMAND" in line and not line.lstrip().startswith("#")]
    assert uses == ['fc_dispatch "${SSH_ORIGINAL_COMMAND-}"'], uses
    assert "bash -c" not in serve


def test_shellcheck_finds_nothing() -> None:
    if shutil.which("shellcheck") is None:
        pytest.skip("shellcheck is not installed on this host")
    completed = subprocess.run(
        ["shellcheck", "-x", "infra/deploy/copy-serve.sh", "infra/deploy/capacity-probe.sh",
         "infra/deploy/pull-copy.sh", "scripts/stand-copy/restore-test.sh", "infra/deploy/lib/forced-command.sh"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


# --- the heavy step: a real PostgreSQL, inside an owner-designated window ---------------

WINDOW = os.environ.get("W54_STAND_COPY_WINDOW") == "1"
PG_IMAGE = os.environ.get("STAND_COPY_RESTORE_IMAGE", "auditmanager-postgres:17.11-pgvector0.8.6-8ee86c9")

SOURCE_SCHEMA = """
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE alembic_version (version_num text PRIMARY KEY);
INSERT INTO alembic_version VALUES ('0019_execution_workers');
CREATE TABLE project (project_id text PRIMARY KEY, name text, created_at timestamptz DEFAULT now(), meta jsonb);
INSERT INTO project VALUES ('prj_1', 'Школа №5', '2026-10-12 10:00:00+03', '{"b": 1, "a": [1.5, 2]}');
CREATE TABLE blob (blob_id text PRIMARY KEY, state text, sha256 text, size_bytes bigint);
INSERT INTO blob VALUES ('blob_client', 'available', repeat('a', 64), 10), ('blob_corpus', 'available', repeat('b', 64), 20);
CREATE TABLE audit_event (audit_event_id text PRIMARY KEY, sequence_no bigint GENERATED ALWAYS AS IDENTITY,
    event_type text, payload jsonb DEFAULT '{}');
INSERT INTO audit_event (audit_event_id, event_type) VALUES ('evt_1', 'project.created'), ('evt_2', 'norm_custody.admitted');
CREATE TABLE command_record (command_id text PRIMARY KEY, command_type text);
INSERT INTO command_record VALUES ('cmd_1', 'create_project'), ('cmd_2', 'norm_custody.admit');
CREATE TABLE norm_custody_admission (norm_custody_admission_id text PRIMARY KEY, blob_id text);
INSERT INTO norm_custody_admission VALUES ('nad_1', 'blob_corpus');
CREATE TABLE norm_document (norm_document_id text PRIMARY KEY, embedding vector(3));
INSERT INTO norm_document VALUES ('nd_1', '[1,2,3]');
"""


@pytest.mark.skipif(not WINDOW, reason="heavy step (W54-PLAN.md 3.9): set W54_STAND_COPY_WINDOW=1 inside the window")
def test_a_dump_restored_here_reproduces_the_fingerprint(tmp_path: Path) -> None:
    """A real PostgreSQL: the stand's fingerprint query over a source database; its
    custom dump through `restore-test.sh` into a second, disposable one; the same
    fingerprint. Then the custody and `norm*` rows change and the fingerprint does not,
    and one client row changes and it does."""
    name = f"stand-copy-source-{os.getpid()}"
    query = COPY_SERVE.read_text(encoding="utf-8")
    query = query[query.index("-- >>> stand-fingerprint-v1\n"):query.index("-- <<< stand-fingerprint-v1\n")]

    def psql(sql: str) -> str:
        return subprocess.run(
            ["docker", "exec", "-i", name, "psql", "--quiet", "--no-align", "--tuples-only", "--no-psqlrc",
             "--set", "ON_ERROR_STOP=1", "--username", "src", "--dbname", "src"],
            input=sql, capture_output=True, text=True, check=True,
        ).stdout

    subprocess.run(["docker", "run", "--detach", "--rm", "--name", name, "--network", "none",
                    "--env", "POSTGRES_USER=src", "--env", "POSTGRES_DB=src", "--env", "POSTGRES_PASSWORD=src",
                    PG_IMAGE], check=True, capture_output=True)
    try:
        deadline = time.monotonic() + 180
        while subprocess.run(["docker", "exec", name, "pg_isready", "--quiet", "--host", "127.0.0.1",
                              "--username", "src", "--dbname", "src"]).returncode != 0:
            assert time.monotonic() < deadline, "the source PostgreSQL did not start"
            time.sleep(1)
        psql(SOURCE_SCHEMA)
        lines = psql(query)
        assert [line.split("|")[0] for line in lines.splitlines()] == [
            "alembic_version", "audit_event", "blob", "command_record", "project"]

        copy = tmp_path / "pulled" / A_STAMP
        copy.mkdir(parents=True)
        dump = subprocess.run(["docker", "exec", name, "pg_dump", "--format=custom", "--no-owner", "--no-privileges",
                               "--username", "src", "--dbname", "src"], capture_output=True, check=True).stdout
        (copy / "db.dump").write_bytes(dump)
        (copy / "inventory.tsv").write_text("")
        fingerprint = subprocess.run(
            ["bash", "-c", f'. "{LIB}"; fc_fingerprint_json "$1"', "_", lines.rstrip("\n")],
            capture_output=True, text=True, check=True).stdout.strip()
        (copy / "record.json").write_text(
            "{\n"
            '  "record_version": 1,\n'
            '  "kind": "copy",\n'
            f'  "stamp": "{A_STAMP}",\n'
            '  "state": "open",\n'
            '  "instance": "window",\n'
            '  "deployed_tree": "window",\n'
            '  "migration_head": "0019_execution_workers",\n'
            f'  "dump": {{"file": "db.dump", "size_bytes": {len(dump)}, "sha256": "{hashlib.sha256(dump).hexdigest()}"}},\n'
            f'  "fingerprint": {fingerprint},\n'
            f'  "inventory": {{"file": "inventory.tsv", "count": 0, "bytes": 0, "sha256": "{hashlib.sha256(b"").hexdigest()}"}}\n'
            "}\n"
        )
        restored = subprocess.run(["bash", str(RESTORE_TEST), str(copy)], capture_output=True, text=True, timeout=600)
        assert restored.returncode == 0, restored.stdout + restored.stderr
        assert "fingerprint reproduced" in restored.stdout

        psql("INSERT INTO audit_event (audit_event_id, event_type) VALUES ('evt_3', 'norm_custody.bound');"
             "INSERT INTO command_record VALUES ('cmd_3', 'norm_custody.admit');"
             "INSERT INTO blob VALUES ('blob_corpus2', 'available', repeat('c', 64), 30);"
             "INSERT INTO norm_custody_admission VALUES ('nad_2', 'blob_corpus2');"
             "INSERT INTO norm_document VALUES ('nd_2', '[3,2,1]');")
        assert psql(query) == lines, "a custody or norm row changed the fingerprint"
        psql("UPDATE project SET name = 'Школа №6';")
        assert psql(query) != lines, "a client row did not change the fingerprint"
    finally:
        subprocess.run(["docker", "rm", "--force", name], capture_output=True)
