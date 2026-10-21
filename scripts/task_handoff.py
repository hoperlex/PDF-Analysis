#!/usr/bin/env python3
"""Produce SHA-bound technical handoff evidence for a strictly scoped task.

The task file is the source of truth. Its ``Allowed paths`` section must consist
only of exact repository paths or directory prefixes ending in ``/**``. An
ambiguous legacy task is refused rather than silently given a broad allowlist.
Checks are explicit argv arrays, never shell strings. This tool does not approve a
task, merge, publish, or infer that a failed check is green.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


TASK_ID = re.compile(r"[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+\Z")
SHA = re.compile(r"[0-9a-f]{40}\Z")
PATH_LINE = re.compile(r"- `([^`]+)`\Z")


class HandoffError(Exception):
    pass


@dataclass(frozen=True)
class Task:
    task_id: str
    base: str
    allowed: tuple[str, ...]


def _section(lines: list[str], title: str) -> list[str]:
    heading = f"## {title}"
    try:
        start = lines.index(heading) + 1
    except ValueError as exc:
        raise HandoffError(f"task is missing {heading}") from exc
    end = next((i for i in range(start, len(lines)) if lines[i].startswith("## ")), len(lines))
    return [line.strip() for line in lines[start:end] if line.strip()]


def _safe_path(value: str) -> bool:
    if not value or value.startswith(("/", "./")) or "\\" in value or "\n" in value:
        return False
    if any(part in ("", ".", "..") for part in value.split("/")):
        return False
    return "*" not in value and "?" not in value


def read_task(path: Path) -> Task:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        raise HandoffError("empty task file")
    match = re.fullmatch(r"# Task ([A-Z0-9-]+)\b.*", lines[0])
    if not match or not TASK_ID.fullmatch(match.group(1)):
        raise HandoffError("task heading must begin '# Task <TASK_ID>'")
    task_id = match.group(1)
    if path.name != f"{task_id}.md":
        raise HandoffError("task filename and task ID differ")
    frozen = _section(lines, "Frozen inputs")
    bases = [m.group(1) for line in frozen if (m := re.fullmatch(r"- base commit: `([0-9a-f]{40})`", line))]
    if len(bases) != 1 or not SHA.fullmatch(bases[0]):
        raise HandoffError("Frozen inputs must contain one exact 40-hex base commit")
    raw_allowed = _section(lines, "Allowed paths")
    if not raw_allowed:
        raise HandoffError("Allowed paths is empty")
    allowed: list[str] = []
    for line in raw_allowed:
        item = PATH_LINE.fullmatch(line)
        if not item:
            raise HandoffError(f"unparseable allowed path: {line!r}")
        value = item.group(1)
        prefix = value[:-3] if value.endswith("/**") else value
        if not _safe_path(prefix):
            raise HandoffError(f"unsafe allowed path: {value!r}")
        allowed.append(value)
    if len(set(allowed)) != len(allowed):
        raise HandoffError("duplicate allowed path")
    return Task(task_id, bases[0], tuple(allowed))


def git(root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, check=False)


def _git_ok(root: Path, *args: str) -> bytes:
    result = git(root, *args)
    if result.returncode:
        raise HandoffError(f"git {' '.join(args)} failed: {result.stderr.decode(errors='replace').strip()}")
    return result.stdout


def exact_head(root: Path) -> str:
    head = _git_ok(root, "rev-parse", "HEAD").decode().strip()
    if not SHA.fullmatch(head):
        raise HandoffError("HEAD is not a full commit SHA")
    return head


def clean_tree(root: Path) -> None:
    status = _git_ok(root, "status", "--porcelain", "--untracked-files=all")
    if status:
        raise HandoffError("working tree is dirty; commit or remove changes before handoff")


def _common_git_dir(root: Path) -> Path:
    value = _git_ok(root, "rev-parse", "--git-common-dir").decode().strip()
    return (root / value).resolve()


def _task_source(root: Path, task_path: Path) -> tuple[Path, str]:
    """Bind an external dispatch task to the same Git repository as the lane."""
    task_path = task_path.resolve()
    if task_path.parent.name != "tasks" or task_path.parent.parent.name != "program" or task_path.parent.parent.parent.name != "docs":
        raise HandoffError("task file must be under docs/program/tasks in a repository worktree")
    source_root = task_path.parent.parent.parent.parent
    if _common_git_dir(source_root) != _common_git_dir(root):
        raise HandoffError("task file and measured worktree belong to different Git repositories")
    relative = task_path.relative_to(source_root)
    _git_ok(source_root, "ls-files", "--error-unmatch", "--", str(relative))
    if git(source_root, "diff", "--quiet", "HEAD", "--", str(relative)).returncode:
        raise HandoffError("task file differs from its committed source")
    return source_root, str(relative)


def changed_paths(root: Path, task: Task) -> list[tuple[str, str]]:
    _git_ok(root, "cat-file", "-e", f"{task.base}^{{commit}}")
    _git_ok(root, "merge-base", "--is-ancestor", task.base, "HEAD")
    raw = _git_ok(root, "diff", "--name-status", "-z", f"{task.base}..HEAD").split(b"\0")
    changes: list[tuple[str, str]] = []
    index = 0
    while index < len(raw) and raw[index]:
        status = raw[index].decode("ascii")
        count = 2 if status.startswith(("R", "C")) else 1
        if index + count >= len(raw):
            raise HandoffError("incomplete git diff record")
        for value in raw[index + 1 : index + count + 1]:
            path = value.decode("utf-8")
            if not _safe_path(path):
                raise HandoffError(f"unsafe changed path: {path!r}")
            if not any(path == rule or (rule.endswith("/**") and path.startswith(rule[:-2])) for rule in task.allowed):
                raise HandoffError(f"changed path outside Allowed paths: {path}")
            changes.append((status, path))
        index += count + 1
    if not changes:
        raise HandoffError("BASE..HEAD has no changed paths")
    return changes


def parse_check(value: str) -> list[str]:
    try:
        argv = json.loads(value)
    except json.JSONDecodeError as exc:
        raise HandoffError(f"check is not a JSON argv array: {exc}") from exc
    if not isinstance(argv, list) or not argv or any(not isinstance(arg, str) or not arg for arg in argv):
        raise HandoffError("check must be a non-empty JSON array of non-empty strings")
    return argv


def _private_write(path: Path, data: bytes) -> None:
    """Replace evidence atomically so existing links cannot redirect a write."""
    descriptor, temporary = tempfile.mkstemp(prefix=".handoff-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _evidence_path(root: Path, output: Path) -> Path:
    local = root / ".local"
    output = Path(os.path.abspath(output))
    if not output.is_relative_to(local) or output == local:
        raise HandoffError("output must be in this checkout's ignored .local directory")
    current = local
    for part in output.parent.relative_to(local).parts:
        if current.is_symlink():
            raise HandoffError(f"refusing symlinked evidence directory: {current}")
        current = current / part
    if current.is_symlink():
        raise HandoffError(f"refusing symlinked evidence directory: {current}")
    output.parent.mkdir(parents=True, exist_ok=True)
    return output


def produce(root: Path, task_path: Path, checks: list[list[str]], output: Path) -> tuple[Path, bool]:
    root = root.resolve()
    task_path = task_path.resolve()
    source_root, task_relative = _task_source(root, task_path)
    task = read_task(task_path)
    task_digest = hashlib.sha256(task_path.read_bytes()).hexdigest()
    clean_tree(root)
    head = exact_head(root)
    changes = changed_paths(root, task)
    if git(root, "diff", "--check", f"{task.base}..HEAD").returncode:
        raise HandoffError("git diff --check is red")
    output = _evidence_path(root, output)
    log_dir = output.parent / f"{task.task_id}-{head[:12]}-logs"
    if log_dir.is_symlink():
        raise HandoffError(f"refusing symlinked evidence directory: {log_dir}")
    log_dir.mkdir(parents=True, exist_ok=True)
    observed: list[tuple[list[str], int, Path, str]] = []
    all_green = True
    for index, argv in enumerate(checks, 1):
        if exact_head(root) != head:
            raise HandoffError("HEAD changed while checks were running")
        result = subprocess.run(argv, cwd=root, capture_output=True, check=False)
        log = log_dir / f"check-{index:02d}.log"
        data = b"$ " + json.dumps(argv, ensure_ascii=False).encode() + b"\n" + result.stdout + b"\n[stderr]\n" + result.stderr
        _private_write(log, data)
        observed.append((argv, result.returncode, log, hashlib.sha256(data).hexdigest()))
        all_green &= result.returncode == 0
        clean_tree(root)
        _task_source(root, task_path)
        if hashlib.sha256(task_path.read_bytes()).hexdigest() != task_digest:
            raise HandoffError("task file changed while checks were running")
    if exact_head(root) != head:
        raise HandoffError("HEAD changed during handoff")
    _task_source(root, task_path)
    lines = [
        f"# Technical handoff evidence — {task.task_id}", "",
        f"- Task: `{task_relative}` at `{exact_head(source_root)}`",
        f"- Task SHA-256: `{task_digest}`",
        f"- Base: `{task.base}`", f"- Head: `{head}`",
        "- Path check: PASS", "- Whitespace check: PASS",
        f"- Check status: {'PASS' if checks and all_green else 'INCOMPLETE' if not checks else 'FAIL'}", "",
        "## Changed files", "",
    ]
    lines += [f"- `{status}` `{path}`" for status, path in changes]
    lines += ["", "## Checks actually run", ""]
    if observed:
        for argv, status, log, digest in observed:
            lines += [f"- `{json.dumps(argv, ensure_ascii=False)}` → exit `{status}`; log `{log.relative_to(root)}`; SHA-256 `{digest}`"]
    else:
        lines += ["- None. Required checks remain to be verified against the task file."]
    lines += [
        "", "## Items requiring a human or independent reviewer", "",
        "- New or changed contracts: **unverified**.",
        "- Risks and known limitations: **unverified**.",
        "- Integration instructions: **unverified**.",
        "- Required test coverage and mutation evidence: **unverified**; compare with the task file.",
        "- This evidence does not approve, merge or publish the candidate.", "",
    ]
    _private_write(output, "\n".join(lines).encode("utf-8"))
    return output, bool(checks) and all_green


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", type=Path, required=True, help="task file under docs/program/tasks")
    parser.add_argument("--worktree", type=Path, help="committed lane worktree to measure; defaults to this checkout")
    parser.add_argument("--check-json", action="append", default=[], help='one command as a JSON argv array, e.g. ["git","diff","--check"]')
    parser.add_argument("--output", type=Path, help="ignored .local output path")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        task = read_task(args.task)
        checks = [parse_check(value) for value in args.check_json]
        worktree = args.worktree or root
        output = args.output or worktree / ".local/handoff" / f"{task.task_id}-evidence.md"
        path, green = produce(worktree, args.task, checks, output)
        print(f"{path}: {'CHECKS PASS' if green else 'INCOMPLETE OR FAILED'}")
        return 0 if green else 1
    except (HandoffError, OSError) as exc:
        print(f"HANDOFF REFUSED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
