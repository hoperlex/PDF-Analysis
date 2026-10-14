#!/usr/bin/env python3
"""The host side of ``make gate``: a preflight, one gate slot, and the battery's first suites.

Why this exists (GATE-PKG-01). Between W48 and W55a about 22 complete gates failed or were
voided, and roughly two thirds of them failed on the HOST, not on the code: a worktree
without the corpus link or ``web/node_modules``, ``StorageUnavailableError`` and exit 137
when another lane or project had taken the memory, a disk too full for MinIO. Each such run
cost 15-40 minutes before it said anything, because the gate brought up containers and ran
the whole battery before it looked at anything cheap. The rest were real reds found late,
after the full battery, that a minute of static checks or the changed contexts' own suites
would have shown first.

Subcommands, in the order the gate calls them:

``preflight``      refuse to START, in seconds, instead of voiding at minute 25: toolchain,
                   corpus link, ``.env``, a clean tree, free disk on the worktree and the
                   Docker data filesystems.
``slot``           take this repository's single gate slot (a ``flock`` in the git common
                   directory, so every worktree shares it) and WAIT, with a heartbeat, until
                   the host has memory headroom and no other ``make gate`` runs. Then leave
                   a holder process that keeps the slot for exactly as long as the calling
                   ``make`` lives and samples ``MemAvailable`` while it does.
``battery-first``  the integration suites of the contexts changed since the last published
                   tree, so the battery runs them before everything else.
``report``         the lowest ``MemAvailable`` the holder saw, printed before ``GATE OK``.

Every refusal starts with ``GATE NOT STARTED:`` and exits non-zero. A refusal is never a
test result: it says the host could not give this run a fair measurement.
"""

from __future__ import annotations

import argparse
import errno
import fcntl
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
FULL_SHA = re.compile(r"[0-9a-f]{40}\Z")

#: Practice since W49 ("wait for >= 3 GB available and no real gate") made executable.
DEFAULT_MIN_AVAILABLE_MIB = 3072
#: MinIO refuses writes under ~1 GB free and a gate used up to ~4 GB (W53 disk samples).
DEFAULT_MIN_FREE_DISK_MIB = 6144
DEFAULT_WAIT_MAX_S = 4 * 3600
DEFAULT_HEARTBEAT_S = 300
DEFAULT_POLL_S = 15
DEFAULT_SAMPLE_S = 15

#: Paths every complete gate needs and a fresh worktree does not have.
CORPUS = Path(".local/norms/corpus")
NODE_MODULES = Path("web/node_modules")
RUNTIME_PY = Path(".venv/bin/python")

#: The battery ignores this suite: the foundation target runs it on its own.
BATTERY_IGNORED_SUITES = frozenset({"foundation"})


class Refusal(Exception):
    """The host cannot give this gate a fair run; nothing was measured."""


# --- environment knobs ---------------------------------------------------------------


def env_int(name: str, default: int, environ: dict[str, str] | None = None) -> int:
    raw = (os.environ if environ is None else environ).get(name, "")
    if raw == "":
        return default
    try:
        value = int(raw)
    except ValueError as error:
        raise Refusal(f"{name}={raw!r} is not an integer") from error
    if value < 0:
        raise Refusal(f"{name}={raw!r} is negative")
    return value


def env_float(name: str, environ: dict[str, str] | None = None) -> float | None:
    raw = (os.environ if environ is None else environ).get(name, "")
    if raw == "":
        return None
    try:
        return float(raw)
    except ValueError as error:
        raise Refusal(f"{name}={raw!r} is not a number") from error


@dataclass(frozen=True)
class Limits:
    min_available_mib: int
    min_free_disk_mib: int
    max_load: float | None
    wait_max_s: int
    heartbeat_s: int
    poll_s: int
    sample_s: int

    @classmethod
    def from_env(cls, environ: dict[str, str] | None = None) -> "Limits":
        return cls(
            min_available_mib=env_int("GATE_MIN_AVAILABLE_MIB", DEFAULT_MIN_AVAILABLE_MIB, environ),
            min_free_disk_mib=env_int("GATE_MIN_FREE_DISK_MIB", DEFAULT_MIN_FREE_DISK_MIB, environ),
            max_load=env_float("GATE_MAX_LOAD", environ),
            wait_max_s=env_int("GATE_WAIT_MAX_S", DEFAULT_WAIT_MAX_S, environ),
            heartbeat_s=max(1, env_int("GATE_HEARTBEAT_S", DEFAULT_HEARTBEAT_S, environ)),
            poll_s=max(1, env_int("GATE_POLL_S", DEFAULT_POLL_S, environ)),
            sample_s=max(1, env_int("GATE_SAMPLE_S", DEFAULT_SAMPLE_S, environ)),
        )


# --- host measurements ------------------------------------------------------------------


def parse_meminfo(text: str) -> dict[str, int]:
    """``/proc/meminfo`` as {name: kB}. Lines that are not ``Name: <n> [kB]`` are skipped."""
    values: dict[str, int] = {}
    for line in text.splitlines():
        name, _, rest = line.partition(":")
        fields = rest.split()
        if name and fields and fields[0].isdigit():
            values[name.strip()] = int(fields[0])
    return values


def available_mib(proc_root: Path = Path("/proc")) -> int:
    values = parse_meminfo((proc_root / "meminfo").read_text(encoding="ascii"))
    if "MemAvailable" not in values:
        # A kernel without MemAvailable cannot be judged; refusing is the honest answer.
        raise Refusal("/proc/meminfo has no MemAvailable line")
    return values["MemAvailable"] // 1024


def load_average(proc_root: Path = Path("/proc")) -> float:
    return float((proc_root / "loadavg").read_text(encoding="ascii").split()[0])


def free_disk_mib(path: Path, statvfs: Callable[[str], os.statvfs_result] = os.statvfs) -> int:
    result = statvfs(str(path))
    return result.f_bavail * result.f_frsize // (1024 * 1024)


def docker_root_dir(run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run) -> Path:
    try:
        result = run(
            ["docker", "info", "--format", "{{.DockerRootDir}}"],
            text=True, capture_output=True, timeout=60, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise Refusal(f"docker info did not answer: {error}") from error
    root = result.stdout.strip()
    if result.returncode or not root:
        raise Refusal(f"docker info failed (exit {result.returncode}): {result.stderr.strip()}")
    return Path(root)


# --- processes ----------------------------------------------------------------------------


def read_argv(proc_root: Path, pid: int) -> list[str]:
    try:
        raw = (proc_root / str(pid) / "cmdline").read_bytes()
    except OSError:
        return []
    return [part.decode("utf-8", "replace") for part in raw.split(b"\0") if part]


def parent_pid(proc_root: Path, pid: int) -> int | None:
    try:
        for line in (proc_root / str(pid) / "status").read_text(encoding="utf-8").splitlines():
            if line.startswith("PPid:"):
                return int(line.split()[1])
    except (OSError, ValueError, IndexError):
        return None
    return None


def ancestry(proc_root: Path, pid: int) -> set[int]:
    seen: set[int] = set()
    current: int | None = pid
    while current and current not in seen:
        seen.add(current)
        current = parent_pid(proc_root, current)
    return seen


def is_gate_make(argv: list[str]) -> bool:
    """A ``make`` whose targets include ``gate`` itself.

    Matching argv tokens, not a pattern over the command line: ``pgrep -f "make gate"``
    matches the waiting loop's own shell and never lets it proceed (2026-10-06), and it
    also matches ``make gate-static`` run by hand.
    """
    if not argv or Path(argv[0]).name not in {"make", "gmake"}:
        return False
    return "gate" in argv[1:]


def children_map(proc_root: Path) -> dict[int, list[int]]:
    children: dict[int, list[int]] = {}
    for entry in proc_root.iterdir():
        if entry.name.isdigit():
            parent = parent_pid(proc_root, int(entry.name))
            if parent is not None:
                children.setdefault(parent, []).append(int(entry.name))
    return children


def queued_for_slot(proc_root: Path, pid: int, children: dict[int, list[int]]) -> bool:
    """True when ``pid`` has a descendant waiting in ``gate_host.py slot``.

    Such a gate is QUEUED behind this repository's slot, so it cannot run while this one
    holds it. Counting it as a running gate would deadlock: the holder would wait for the
    queued gate to finish, and the queued gate waits for the holder's slot.
    """
    pending = list(children.get(pid, ()))
    seen: set[int] = set()
    while pending:
        child = pending.pop()
        if child in seen:
            continue
        seen.add(child)
        argv = read_argv(proc_root, child)
        if any(Path(part).name == "gate_host.py" for part in argv) and "slot" in argv:
            return True
        pending.extend(children.get(child, ()))
    return False


def foreign_gates(proc_root: Path = Path("/proc"), own_pid: int | None = None) -> list[tuple[int, str]]:
    """Every running ``make gate`` on the host that is not this one and not queued behind it."""
    mine = ancestry(proc_root, own_pid if own_pid is not None else os.getpid())
    children = children_map(proc_root)
    found: list[tuple[int, str]] = []
    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        if pid in mine or not is_gate_make(read_argv(proc_root, pid)):
            continue
        if queued_for_slot(proc_root, pid, children):
            continue
        try:
            cwd = os.readlink(entry / "cwd")
        except OSError:
            cwd = "?"
        found.append((pid, cwd))
    return sorted(found)


def pid_alive(pid: int, proc_root: Path = Path("/proc")) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        pass
    try:
        state = (proc_root / str(pid) / "stat").read_text(encoding="utf-8").rsplit(")", 1)[1].split()[0]
    except (OSError, IndexError):
        return False
    return state != "Z"


def proc_root_from_env(environ: dict[str, str] | None = None) -> Path:
    """``/proc`` for the headroom judgement; ``GATE_PROC_ROOT`` lets a test hand it a fake one."""
    return Path((os.environ if environ is None else environ).get("GATE_PROC_ROOT", "") or "/proc")


# --- git -------------------------------------------------------------------------------------


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=False)


def head_sha(root: Path) -> str:
    result = git(root, "rev-parse", "HEAD")
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def slot_dir(root: Path, environ: dict[str, str] | None = None) -> Path:
    """The git COMMON directory, which every worktree of this repository shares."""
    override = (os.environ if environ is None else environ).get("GATE_SLOT_DIR", "")
    if override:
        return Path(override)
    result = git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if result.returncode or not result.stdout.strip():
        raise Refusal(f"cannot locate the git common directory: {result.stderr.strip()}")
    return Path(result.stdout.strip())


# --- preflight -------------------------------------------------------------------------------


def preflight_findings(
    root: Path,
    limits: Limits,
    *,
    docker_root: Callable[[], Path] = docker_root_dir,
    statvfs: Callable[[str], os.statvfs_result] = os.statvfs,
    log: Callable[[str], None] = print,
) -> list[str]:
    """Every reason this checkout cannot start a complete gate. Empty means it may start."""
    findings: list[str] = []
    if not os.access(root / RUNTIME_PY, os.X_OK):
        findings.append(f"{RUNTIME_PY} is missing; run: make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12")
    if not (root / NODE_MODULES).is_dir():
        findings.append(f"{NODE_MODULES} is missing; run: npm --prefix web ci (or link a provisioned checkout's)")
    if not (root / CORPUS).is_dir():
        findings.append(
            f"{CORPUS} is missing; the embedding bake-off test needs the real corpus: "
            "mkdir -p .local/norms && ln -s /root/projects/PDF-Analysis/.local/norms/corpus .local/norms/corpus"
        )
    if not (root / ".env").is_file():
        findings.append(".env is missing; copy .env.example and give this lane its own instance and ports")
    status = git(root, "status", "--porcelain", "--untracked-files=all")
    if status.returncode:
        findings.append(f"git status failed: {status.stderr.strip()}")
    elif status.stdout.strip():
        changed = len(status.stdout.splitlines())
        findings.append(
            f"the tree has {changed} uncommitted path(s); a complete gate certifies a commit, so commit or remove them"
        )
    targets: list[tuple[str, Path]] = [("worktree", root)]
    try:
        targets.append(("docker data", docker_root()))
    except Refusal as error:
        findings.append(str(error))
    for label, path in targets:
        try:
            free = free_disk_mib(path, statvfs)
        except OSError as error:
            findings.append(f"cannot measure free disk for the {label} filesystem at {path}: {error}")
            continue
        # AGENTS.md §8: the measurement itself is recorded beside the run log.
        log(f"GATE PREFLIGHT: {label} filesystem {path}: {free} MiB available "
            f"(minimum {limits.min_free_disk_mib}) at {now_utc()}")
        if free < limits.min_free_disk_mib:
            findings.append(
                f"the {label} filesystem at {path} has {free} MiB free, below GATE_MIN_FREE_DISK_MIB={limits.min_free_disk_mib}"
            )
    return findings


def cmd_preflight(_args: argparse.Namespace) -> int:
    limits = Limits.from_env()
    findings = preflight_findings(ROOT, limits)
    if findings:
        for finding in findings:
            print(f"GATE NOT STARTED: {finding}", file=sys.stderr)
        return 2
    print(f"GATE PREFLIGHT OK: {head_sha(ROOT)}")
    return 0


# --- the slot --------------------------------------------------------------------------------


def headroom_problems(
    limits: Limits,
    *,
    proc_root: Path = Path("/proc"),
    own_pid: int | None = None,
) -> list[str]:
    """Why the host cannot take a gate now. Empty means it can."""
    problems: list[str] = []
    free = available_mib(proc_root)
    if free < limits.min_available_mib:
        problems.append(f"MemAvailable {free} MiB < GATE_MIN_AVAILABLE_MIB={limits.min_available_mib}")
    if limits.max_load is not None:
        load = load_average(proc_root)
        if load > limits.max_load:
            problems.append(f"load average {load:.1f} > GATE_MAX_LOAD={limits.max_load:g}")
    others = foreign_gates(proc_root, own_pid)
    if others:
        listed = ", ".join(f"pid {pid} in {cwd}" for pid, cwd in others)
        problems.append(f"another make gate is running: {listed}")
    return problems


def try_lock(path: Path) -> int | None:
    """An fd holding an exclusive lock on ``path``, or None when another process holds it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as error:
        os.close(fd)
        if error.errno in (errno.EWOULDBLOCK, errno.EAGAIN):
            return None
        raise
    return fd


def read_holder(info: Path) -> str:
    try:
        data = json.loads(info.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "unknown holder"
    return f"pid {data.get('holder_pid')} for {data.get('cwd')} at {data.get('head', '?')[:12]} since {data.get('since')}"


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def hold(fd: int, owner_pid: int, samples: Path, info: Path, sample_s: int) -> None:
    """Keep the slot while the owner lives; sample MemAvailable meanwhile. Never returns.

    Liveness is polled every second, so the slot frees within a second of ``make`` ending
    for any reason -- success, a red step, Ctrl-C or SIGKILL. The holder leaves the
    session and drops stdio, so neither Ctrl-C nor a ``| tee`` waits on it.
    """
    try:
        os.setsid()
    except OSError:
        pass
    devnull = os.open(os.devnull, os.O_RDWR)
    for target in (0, 1, 2):
        os.dup2(devnull, target)
    try:
        with samples.open("a", encoding="ascii") as out:
            next_sample = 0.0
            while pid_alive(owner_pid):
                if time.monotonic() >= next_sample:
                    try:
                        out.write(f"{now_utc()}\t{available_mib()}\n")
                        out.flush()
                    except (OSError, Refusal):
                        pass
                    next_sample = time.monotonic() + sample_s
                time.sleep(1)
    finally:
        try:
            if json.loads(info.read_text(encoding="utf-8")).get("holder_pid") == os.getpid():
                info.unlink()
        except (OSError, ValueError):
            pass
        os.close(fd)
        os._exit(0)


def acquire_slot(
    root: Path,
    owner_pid: int,
    limits: Limits,
    *,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    log: Callable[[str], None] = print,
) -> int:
    """Wait for the slot and for headroom, then fork the holder. Returns the holder's pid."""
    directory = slot_dir(root)
    lock = directory / "gate-slot.flock"
    info = directory / "gate-slot.json"
    started = clock()
    last_beat = started
    fd: int | None = None
    waited_for = ""
    log(f"GATE SLOT: waiting for {lock}; MemAvailable >= {limits.min_available_mib} MiB"
        + (f", load <= {limits.max_load:g}" if limits.max_load is not None else "")
        + f", no other make gate; at most {limits.wait_max_s} s")
    while True:
        if not pid_alive(owner_pid):
            if fd is not None:
                os.close(fd)
            raise Refusal(f"the calling make (pid {owner_pid}) is gone")
        if fd is None:
            fd = try_lock(lock)
            waited_for = "" if fd is not None else f"the slot, held by {read_holder(info)}"
        if fd is not None:
            problems = headroom_problems(limits, proc_root=proc_root_from_env(), own_pid=owner_pid)
            if not problems:
                break
            waited_for = "; ".join(problems)
        elapsed = clock() - started
        if elapsed >= limits.wait_max_s:
            if fd is not None:
                os.close(fd)
            raise Refusal(f"waited {int(elapsed)} s for {waited_for}")
        if clock() - last_beat >= limits.heartbeat_s:
            log(f"GATE SLOT: still waiting after {int(elapsed)} s for {waited_for}")
            last_beat = clock()
        sleep(limits.poll_s)
    head = head_sha(root)
    runs = directory / "gate-runs"
    runs.mkdir(parents=True, exist_ok=True)
    samples = runs / f"{now_utc().replace(':', '')}-{head[:12]}.mem.tsv"
    sys.stdout.flush()
    sys.stderr.flush()
    child = os.fork()
    if child == 0:
        hold(fd, owner_pid, samples, info, limits.sample_s)
    record = {"owner_pid": owner_pid, "holder_pid": child, "cwd": str(root), "head": head,
              "since": now_utc(), "samples": str(samples)}
    info.write_text(json.dumps(record), encoding="utf-8")
    os.close(fd)
    log(f"GATE SLOT HELD: {head} by holder pid {child} while make pid {owner_pid} lives; "
        f"MemAvailable {available_mib()} MiB; samples in {samples}")
    return child


def cmd_slot(args: argparse.Namespace) -> int:
    try:
        acquire_slot(ROOT, args.owner_pid, Limits.from_env())
    except Refusal as error:
        print(f"GATE NOT STARTED: {error}", file=sys.stderr)
        return 3
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    try:
        info = slot_dir(ROOT) / "gate-slot.json"
        record = json.loads(info.read_text(encoding="utf-8"))
    except (OSError, ValueError, Refusal) as error:
        print(f"GATE MEMORY: no slot record ({error})")
        return 0
    if record.get("owner_pid") != args.owner_pid:
        print(f"GATE MEMORY: the slot record belongs to make pid {record.get('owner_pid')}, not {args.owner_pid}")
        return 0
    values = []
    try:
        for line in Path(record["samples"]).read_text(encoding="ascii").splitlines():
            stamp, _, value = line.partition("\t")
            if value.strip().isdigit():
                values.append(int(value))
    except OSError:
        pass
    if not values:
        print("GATE MEMORY: no samples recorded")
    else:
        print(f"GATE MEMORY: lowest MemAvailable {min(values)} MiB over {len(values)} samples ({record['samples']})")
    return 0


# --- the battery's first suites ----------------------------------------------------------------


def load_context_suites() -> dict[str, tuple[str, ...]]:
    """R-70's context→suite map, read from the light-acceptance selector so there is one map."""
    sys.path.insert(0, str(SCRIPTS))
    try:
        import light_acceptance  # noqa: PLC0415
    finally:
        sys.path.remove(str(SCRIPTS))
    return dict(light_acceptance.CONTEXT_SUITES)


def first_suites(paths: Iterable[str], root: Path, context_suites: dict[str, tuple[str, ...]]) -> list[str]:
    """Integration suites the changed paths point at, that exist and that the battery runs.

    A changed ``src/auditmanager/<context>/`` selects that context's suites; a changed
    ``tests/integration/<suite>/`` selects the suite itself. Anything else selects nothing:
    this only ORDERS the battery, it never removes a test from it.
    """
    chosen: set[str] = set()
    for path in paths:
        parts = path.split("/")
        if len(parts) > 3 and parts[:2] == ["src", "auditmanager"]:
            chosen.update(context_suites.get(parts[2], ()))
        elif len(parts) > 3 and parts[:2] == ["tests", "integration"]:
            chosen.add(parts[2])
    existing = []
    for suite in sorted(chosen - BATTERY_IGNORED_SUITES):
        directory = root / "tests" / "integration" / suite
        if directory.is_dir() and any(directory.rglob("test_*.py")):
            existing.append(suite)
    return existing


def battery_base(root: Path, environ: dict[str, str] | None = None) -> str | None:
    """``GATE_BASE`` when given, else the merge base with ``origin/main``: the last published tree."""
    explicit = (os.environ if environ is None else environ).get("GATE_BASE", "")
    if explicit:
        if not FULL_SHA.fullmatch(explicit) or git(root, "merge-base", "--is-ancestor", explicit, "HEAD").returncode:
            raise Refusal(f"GATE_BASE={explicit} is not a full SHA that is an ancestor of HEAD")
        return explicit
    result = git(root, "merge-base", "HEAD", "origin/main")
    return result.stdout.strip() if result.returncode == 0 and result.stdout.strip() else None


def cmd_battery_first(_args: argparse.Namespace) -> int:
    try:
        base = battery_base(ROOT)
    except Refusal as error:
        print(f"GATE NOT STARTED: {error}", file=sys.stderr)
        return 2
    if base is None:
        print("GATE: no origin/main and no GATE_BASE; the battery runs in its usual order", file=sys.stderr)
        return 0
    diff = git(ROOT, "diff", "--name-only", "-z", f"{base}..HEAD")
    if diff.returncode:
        print(f"GATE NOT STARTED: cannot diff {base}..HEAD: {diff.stderr.strip()}", file=sys.stderr)
        return 2
    paths = [path for path in diff.stdout.split("\0") if path]
    suites = first_suites(paths, ROOT, load_context_suites())
    print(f"GATE: {len(paths)} path(s) changed since {base[:12]}; first suites: {' '.join(suites) or 'none'}",
          file=sys.stderr)
    for suite in suites:
        print(suite)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("preflight").set_defaults(func=cmd_preflight)
    slot = commands.add_parser("slot")
    slot.add_argument("--owner-pid", type=int, required=True)
    slot.set_defaults(func=cmd_slot)
    report = commands.add_parser("report")
    report.add_argument("--owner-pid", type=int, required=True)
    report.set_defaults(func=cmd_report)
    commands.add_parser("battery-first").set_defaults(func=cmd_battery_first)
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Refusal as error:
        print(f"GATE NOT STARTED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
