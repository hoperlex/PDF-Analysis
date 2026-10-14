#!/usr/bin/env python3
"""Find, and on ``--apply`` remove, what finished lanes left on this shared host.

GATE-PKG-01. The host runs out of memory and disk under many sessions, and this
repository's own leftovers add to it: lane worktrees whose work is long merged, the
PostgreSQL/MinIO volumes of compose projects whose worktree is gone, and wave-10-era
mutation copies under ``/root``. Nothing here is removed on a guess:

* a worktree goes only when it is under ``.local/worktrees/``, clean, contained in every
  ``--merged-into`` ref, idle for ``--idle-hours``, not locked or protected, no process has
  its cwd inside it, no other worktree links its ``.venv``/``node_modules``/corpus, and
  its compose project has no container. ``git worktree remove`` (never ``--force``) does
  the removal; branches and refs are kept.
* a volume goes (``--docker``) only when it carries this repository's compose signature
  (``<project>-postgres-data`` / ``<project>-s3-data`` with that project label and an
  instance prefix of this repository), no container of any state references the project
  or the volume, and no remaining worktree's ``.env`` names the project. The persistent
  promotion database is protected by name.
* a mutation copy goes (``--mutation-copies``) only when it is ``/root/*-mut*``, has no
  ``.git``, carries ``src/auditmanager`` and this project's ``pyproject.toml`` name, is
  idle and unused. ``shutil.rmtree`` does not follow the copy's symlinks into the tree.

The default is a report. Removing worktrees is the integrator's act (AGENTS.md §7.1), so
``--apply`` is for the integrator; the report is for anyone. Docker build cache and
anonymous volumes are shared with other projects on this host and are only counted.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable


ROOT = Path(__file__).resolve().parents[1]
PROJECT_NAME = 'name = "auditmanager-foundation"'
VOLUME_KEYS = ("postgres-data", "s3-data")
DEFAULT_INSTANCE_PREFIXES = ("auditmanager-", "gate-")
DEFAULT_KEEP_INSTANCES = ("auditmanager-promotion*",)
DEFAULT_KEEP = ("plan/*",)
SHARED_LINKS = (".venv", "web/node_modules", ".local/norms/corpus")


def git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True, check=False)


# --- inputs ------------------------------------------------------------------------------------


@dataclass
class Worktree:
    path: Path
    head: str
    branch: str | None
    locked: str | None = None
    prunable: bool = False
    main: bool = False


def list_worktrees(repo: Path) -> list[Worktree]:
    result = git(repo, "worktree", "list", "--porcelain")
    if result.returncode:
        raise SystemExit(f"git worktree list failed: {result.stderr.strip()}")
    trees: list[Worktree] = []
    for block in result.stdout.strip().split("\n\n"):
        fields: dict[str, str] = {}
        for line in block.splitlines():
            key, _, value = line.partition(" ")
            fields[key] = value
        if "worktree" not in fields:
            continue
        branch = fields.get("branch", "")
        trees.append(Worktree(
            path=Path(fields["worktree"]),
            head=fields.get("HEAD", ""),
            branch=branch.removeprefix("refs/heads/") or None,
            locked=fields.get("locked") if "locked" in fields else None,
            prunable="prunable" in fields,
            main=not trees,
        ))
    return trees


def read_instance(path: Path) -> str | None:
    try:
        for line in (path / ".env").read_text(encoding="utf-8").splitlines():
            name, _, value = line.strip().partition("=")
            if name.strip() == "FOUNDATION_INSTANCE":
                return value.strip().strip("'\"") or None
    except OSError:
        return None
    return None


def process_cwds(proc_root: Path = Path("/proc")) -> list[tuple[int, str, Path]]:
    found: list[tuple[int, str, Path]] = []
    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            cwd = Path(os.readlink(entry / "cwd"))
            name = (entry / "comm").read_text(encoding="utf-8").strip()
        except OSError:
            continue
        found.append((int(entry.name), name, cwd))
    return found


def inside(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
    except ValueError:
        return False
    return True


def last_activity(path: Path) -> float:
    """The newest of the worktree's own git metadata: index, HEAD and its reflog."""
    stamps = []
    try:
        pointer = (path / ".git").read_text(encoding="utf-8").strip()
        gitdir = Path(pointer.removeprefix("gitdir:").strip())
    except OSError:
        gitdir = path / ".git"
    for candidate in (gitdir / "index", gitdir / "HEAD", gitdir / "logs" / "HEAD", path):
        try:
            stamps.append(candidate.stat().st_mtime)
        except OSError:
            pass
    return max(stamps, default=0.0)


class Docker:
    """The docker CLI, narrowed to what this script reads and removes."""

    def __init__(self, run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run) -> None:
        self._run = run

    def _cli(self, *args: str) -> str:
        result = self._run(["docker", *args], text=True, capture_output=True, timeout=120, check=False)
        if result.returncode:
            raise RuntimeError(f"docker {' '.join(args)} failed: {result.stderr.strip()}")
        return result.stdout

    def project_containers(self, project: str) -> list[str]:
        out = self._cli("ps", "-a", "--filter", f"label=com.docker.compose.project={project}",
                        "--format", "{{.Names}} {{.State}}")
        return [line for line in out.splitlines() if line.strip()]

    def volume_containers(self, volume: str) -> list[str]:
        out = self._cli("ps", "-a", "--filter", f"volume={volume}", "--format", "{{.Names}}")
        return [line for line in out.splitlines() if line.strip()]

    def volumes(self) -> list[tuple[str, str]]:
        out = self._cli("volume", "ls", "--format", '{{.Name}}\t{{.Label "com.docker.compose.project"}}')
        rows = []
        for line in out.splitlines():
            name, _, project = line.partition("\t")
            if name:
                rows.append((name, project.strip()))
        return rows

    def remove_volume(self, volume: str) -> None:
        self._cli("volume", "rm", volume)

    def disk_summary(self) -> str:
        return self._cli("system", "df").strip()


# --- verdicts ----------------------------------------------------------------------------------


@dataclass
class Verdict:
    kind: str
    target: str
    detail: str
    reasons: list[str] = field(default_factory=list)
    instance: str | None = None

    @property
    def remove(self) -> bool:
        return not self.reasons


@dataclass(frozen=True)
class Policy:
    merged_into: tuple[str, ...]
    idle_hours: float
    keep: tuple[str, ...]
    keep_instances: tuple[str, ...]
    instance_prefixes: tuple[str, ...]


def merged_refs(repo: Path, refs: Iterable[str]) -> dict[str, str]:
    resolved = {}
    for ref in refs:
        result = git(repo, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
        if result.returncode:
            raise SystemExit(f"--merged-into {ref}: not a commit in this repository")
        resolved[ref] = result.stdout.strip()
    return resolved


def judge_worktrees(
    repo: Path,
    trees: list[Worktree],
    policy: Policy,
    *,
    docker: Docker,
    now: float,
    cwds: list[tuple[int, str, Path]],
) -> list[Verdict]:
    lanes_dir = (trees[0].path / ".local" / "worktrees").resolve() if trees else repo
    refs = merged_refs(repo, policy.merged_into)
    # Where every other worktree's shared environment really lives.
    links: list[tuple[Path, str]] = []
    for tree in trees:
        for name in SHARED_LINKS:
            link = tree.path / name
            if link.is_symlink():
                links.append((link.resolve(), f"{name} of {tree.path.name}"))
    verdicts: list[Verdict] = []
    for tree in trees:
        label = tree.branch or f"detached {tree.head[:8]}"
        verdict = Verdict("worktree", str(tree.path), f"{label} {tree.head[:8]}")
        verdicts.append(verdict)
        reasons = verdict.reasons
        if tree.main:
            reasons.append("the main checkout")
            continue
        if tree.prunable:
            reasons.append("prunable: its directory is gone (git worktree prune clears the record)")
            continue
        if not inside(tree.path.resolve(), lanes_dir):
            reasons.append("outside .local/worktrees")
        if tree.locked is not None:
            reasons.append(f"locked{': ' + tree.locked if tree.locked else ''}")
        for pattern in policy.keep:
            if fnmatch.fnmatch(tree.branch or "", pattern) or fnmatch.fnmatch(tree.path.name, pattern):
                reasons.append(f"protected by --keep {pattern}")
        # Activity is read BEFORE git status, and status takes no optional locks, so this
        # script's own look at a worktree never refreshes its index into looking "active".
        idle = max(0.0, (now - last_activity(tree.path)) / 3600)
        status = git(tree.path, "--no-optional-locks", "status", "--porcelain", "--untracked-files=all")
        if status.returncode:
            reasons.append(f"git status failed: {status.stderr.strip()}")
        elif status.stdout.strip():
            reasons.append(f"{len(status.stdout.splitlines())} uncommitted path(s)")
        for ref, sha in refs.items():
            if git(repo, "merge-base", "--is-ancestor", tree.head, sha).returncode:
                reasons.append(f"HEAD not contained in {ref}")
        if idle < policy.idle_hours:
            reasons.append(f"active {idle:.1f} h ago (< --idle-hours {policy.idle_hours:g})")
        resolved = tree.path.resolve()
        for pid, name, cwd in cwds:
            if inside(cwd, resolved):
                reasons.append(f"process {pid} ({name}) has its cwd inside")
                break
        for target, owner in links:
            if inside(target, resolved):
                reasons.append(f"provides the {owner}")
        verdict.instance = read_instance(tree.path)
        if verdict.instance:
            # Always asked, never skipped: removing a worktree under a live stack leaves
            # containers bound to a directory that no longer exists.
            try:
                containers = docker.project_containers(verdict.instance)
            except (RuntimeError, OSError, subprocess.TimeoutExpired) as error:
                reasons.append(f"cannot tell whether compose project {verdict.instance} runs: {error}")
            else:
                if containers:
                    reasons.append(f"compose project {verdict.instance} has {len(containers)} container(s); run make down there")
    return verdicts


def judge_volumes(
    docker: Docker,
    policy: Policy,
    live_instances: set[str],
) -> list[Verdict]:
    verdicts: list[Verdict] = []
    container_cache: dict[str, list[str]] = {}
    for name, project in docker.volumes():
        if not project or not project.startswith(policy.instance_prefixes):
            continue
        if name not in {f"{project}-{key}" for key in VOLUME_KEYS}:
            continue
        verdict = Verdict("volume", name, f"compose project {project}", instance=project)
        verdicts.append(verdict)
        if any(fnmatch.fnmatch(project, pattern) for pattern in policy.keep_instances):
            verdict.reasons.append("protected instance")
        if project in live_instances:
            verdict.reasons.append("a worktree's .env still names this instance")
        if project not in container_cache:
            container_cache[project] = docker.project_containers(project)
        if container_cache[project]:
            verdict.reasons.append(f"{len(container_cache[project])} container(s) of the project exist")
        users = docker.volume_containers(name)
        if users:
            verdict.reasons.append(f"used by {', '.join(users)}")
    return verdicts


def is_mutation_copy(path: Path) -> bool:
    if (path / ".git").exists() or not (path / "src" / "auditmanager").is_dir():
        return False
    try:
        return PROJECT_NAME in (path / "pyproject.toml").read_text(encoding="utf-8")
    except OSError:
        return False


def newest_mtime(path: Path, depth: int = 2) -> float:
    newest = 0.0
    pending = [(path, 0)]
    while pending:
        current, level = pending.pop()
        try:
            stat = current.lstat()
        except OSError:
            continue
        newest = max(newest, stat.st_mtime)
        if level < depth and current.is_dir() and not current.is_symlink():
            try:
                pending.extend((child, level + 1) for child in current.iterdir())
            except OSError:
                pass
    return newest


def judge_mutation_copies(
    home: Path, policy: Policy, *, now: float, cwds: list[tuple[int, str, Path]]
) -> list[Verdict]:
    verdicts: list[Verdict] = []
    for path in sorted(home.glob("*-mut*")):
        if not path.is_dir() or path.is_symlink():
            continue
        if not is_mutation_copy(path):
            # Older recipes (W10-W12) copied no pyproject.toml. Shown, never guessed at.
            verdicts.append(Verdict("mutation copy", str(path), "unrecognised",
                                    ["no .git-free src/auditmanager with this project's pyproject.toml; inspect by hand"]))
            continue
        verdict = Verdict("mutation copy", str(path), "no .git; src/auditmanager present")
        verdicts.append(verdict)
        idle = max(0.0, (now - newest_mtime(path)) / 3600)
        if idle < policy.idle_hours:
            verdict.reasons.append(f"active {idle:.1f} h ago (< --idle-hours {policy.idle_hours:g})")
        resolved = path.resolve()
        for pid, name, cwd in cwds:
            if inside(cwd, resolved):
                verdict.reasons.append(f"process {pid} ({name}) has its cwd inside")
                break
    return verdicts


# --- sizes and output ------------------------------------------------------------------------


def size_mib(path: str) -> int | None:
    try:
        result = subprocess.run(["du", "-sxm", path], text=True, capture_output=True, timeout=600, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    try:
        return int(result.stdout.split()[0])
    except (IndexError, ValueError):
        return None


def show(verdicts: list[Verdict], sizes: bool, out: Callable[[str], None]) -> int:
    total = 0
    for verdict in sorted(verdicts, key=lambda v: (not v.remove, v.target)):
        size = ""
        if sizes and verdict.remove and verdict.kind != "volume":
            mib = size_mib(verdict.target)
            if mib is not None:
                total += mib
                size = f" [{mib} MiB]"
        state = "REMOVE" if verdict.remove else "KEEP  "
        why = "" if verdict.remove else " -- " + "; ".join(verdict.reasons)
        out(f"  {state} {verdict.target} ({verdict.detail}){size}{why}")
    return total


# --- actions ---------------------------------------------------------------------------------


def apply(repo: Path, verdicts: list[Verdict], docker: Docker, volumes_too: bool,
          live_instances: set[str], out: Callable[[str], None]) -> int:
    failures = 0
    for verdict in verdicts:
        if not verdict.remove:
            continue
        if verdict.kind == "worktree":
            result = git(repo, "worktree", "remove", verdict.target)
            if result.returncode:
                failures += 1
                out(f"  FAILED  git worktree remove {verdict.target}: {result.stderr.strip()}")
                continue
            out(f"  REMOVED worktree {verdict.target}")
            if volumes_too and verdict.instance and verdict.instance not in live_instances:
                for key in VOLUME_KEYS:
                    name = f"{verdict.instance}-{key}"
                    if name in {volume for volume, _ in docker.volumes()} and not docker.volume_containers(name):
                        try:
                            docker.remove_volume(name)
                            out(f"  REMOVED volume {name}")
                        except RuntimeError as error:
                            failures += 1
                            out(f"  FAILED  {error}")
        elif verdict.kind == "volume":
            try:
                docker.remove_volume(verdict.target)
                out(f"  REMOVED volume {verdict.target}")
            except RuntimeError as error:
                failures += 1
                out(f"  FAILED  {error}")
        elif verdict.kind == "mutation copy":
            try:
                shutil.rmtree(verdict.target)
                out(f"  REMOVED mutation copy {verdict.target}")
            except OSError as error:
                failures += 1
                out(f"  FAILED  rmtree {verdict.target}: {error}")
    prune = git(repo, "worktree", "prune")
    if prune.returncode:
        failures += 1
        out(f"  FAILED  git worktree prune: {prune.stderr.strip()}")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--apply", action="store_true", help="remove what the report marks REMOVE")
    parser.add_argument("--merged-into", action="append", default=None, metavar="REF",
                        help="a worktree must be contained in every REF (default: origin/dev)")
    parser.add_argument("--idle-hours", type=float, default=24.0)
    parser.add_argument("--keep", action="append", default=[], metavar="GLOB",
                        help="branch or directory names never removed, in addition to plan/*")
    parser.add_argument("--docker", action="store_true",
                        help="also judge and remove volumes: those of removed worktrees and orphan ones")
    parser.add_argument("--mutation-copies", action="store_true", help="also judge /root/*-mut* copies")
    parser.add_argument("--home", type=Path, default=Path("/root"), help=argparse.SUPPRESS)
    parser.add_argument("--repo", type=Path, default=ROOT, help=argparse.SUPPRESS)
    parser.add_argument("--sizes", action="store_true", help="measure what would be freed (du; slow)")
    args = parser.parse_args(argv)
    policy = Policy(
        merged_into=tuple(args.merged_into or ["origin/dev"]),
        idle_hours=args.idle_hours,
        keep=DEFAULT_KEEP + tuple(args.keep),
        keep_instances=DEFAULT_KEEP_INSTANCES,
        instance_prefixes=DEFAULT_INSTANCE_PREFIXES,
    )
    out = print
    repo = args.repo
    trees = list_worktrees(repo)
    docker = Docker()
    now = time.time()
    cwds = process_cwds()
    refs = merged_refs(repo, policy.merged_into)
    out(f"WORKTREES (contained in {', '.join(f'{r} {s[:8]}' for r, s in refs.items())}; "
        f"idle >= {policy.idle_hours:g} h)")
    verdicts = judge_worktrees(repo, trees, policy, docker=docker, now=now, cwds=cwds)
    removed_trees = {v.target for v in verdicts if v.remove}
    live_instances = {i for t in trees if str(t.path) not in removed_trees and (i := read_instance(t.path))}
    freed = show(verdicts, args.sizes, out)
    if args.docker:
        volumes = judge_volumes(docker, policy, live_instances | {
            v.instance for v in verdicts if v.instance and v.remove})
        out("ORPHAN VOLUMES (this repository's compose signature, no worktree, no container)")
        show(volumes, False, out)
        verdicts += volumes
    if args.mutation_copies:
        copies = judge_mutation_copies(args.home, policy, now=now, cwds=cwds)
        out(f"MUTATION COPIES ({args.home}/*-mut*)")
        freed += show(copies, args.sizes, out)
        verdicts += copies
    count = sum(v.remove for v in verdicts)
    if args.docker:
        out("NOT TOUCHED (shared with other projects on this host): build cache, images, anonymous volumes")
        for line in docker.disk_summary().splitlines():
            out(f"  {line}")
    size_note = f", about {freed} MiB on disk" if args.sizes else ""
    if not args.apply:
        out(f"DRY RUN: {count} item(s) marked REMOVE{size_note}. Nothing was changed; re-run with --apply.")
        return 0
    failures = apply(repo, verdicts, docker, args.docker, live_instances, out)
    out(f"APPLIED: {count - failures} of {count} item(s) removed; {failures} failure(s).")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
