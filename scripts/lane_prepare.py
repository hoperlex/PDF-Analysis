#!/usr/bin/env python3
"""Prepare one isolated task worktree from assigned, not invented, lane resources.

The integrator writes the six resources in the task's ``Lane resources`` section.
This command verifies the exact base and resource isolation before creating a
worktree. It uses only the disposable values in ``.env.example``; it never
copies a real checkout's ``.env`` or a provider/deployment credential.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from task_handoff import HandoffError, _git_ok, _section, _task_source, git, read_task


RESOURCE_LINE = re.compile(r"- ([a-z0-9_]+): `([^`]+)`\Z")
RESOURCE_KEYS = frozenset({
    "foundation_instance", "postgres_port", "s3_api_port", "s3_console_port",
    "postgres_db", "s3_bucket",
})
ENV_KEYS = frozenset({
    "FOUNDATION_INSTANCE", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD",
    "POSTGRES_PORT", "DATABASE_URL", "MINIO_ROOT_USER", "MINIO_ROOT_PASSWORD",
    "S3_ENDPOINT_URL", "S3_API_PORT", "S3_CONSOLE_PORT", "S3_REGION",
    "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY", "S3_BUCKET",
})


@dataclass(frozen=True)
class Resources:
    instance: str
    postgres_port: int
    s3_api_port: int
    s3_console_port: int
    database: str
    bucket: str

    @property
    def ports(self) -> tuple[int, int, int]:
        return self.postgres_port, self.s3_api_port, self.s3_console_port


def read_resources(task_file: Path) -> Resources:
    lines = task_file.read_text(encoding="utf-8").splitlines()
    values: dict[str, str] = {}
    for line in _section(lines, "Lane resources"):
        match = RESOURCE_LINE.fullmatch(line)
        if not match or match.group(1) not in RESOURCE_KEYS or match.group(1) in values:
            raise HandoffError(f"invalid or duplicate lane resource: {line!r}")
        values[match.group(1)] = match.group(2)
    if values.keys() != RESOURCE_KEYS:
        raise HandoffError(f"Lane resources must name exactly {', '.join(sorted(RESOURCE_KEYS))}")
    if not re.fullmatch(r"(?:auditmanager|gate)-[a-z0-9][a-z0-9-]{2,48}", values["foundation_instance"]):
        raise HandoffError("FOUNDATION_INSTANCE is not a safe lane name")
    if not re.fullmatch(r"[a-z][a-z0-9_]{2,62}", values["postgres_db"]):
        raise HandoffError("POSTGRES_DB is not a safe database name")
    if not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", values["s3_bucket"]):
        raise HandoffError("S3_BUCKET is not a safe bucket name")
    try:
        ports = tuple(int(values[key]) for key in ("postgres_port", "s3_api_port", "s3_console_port"))
    except ValueError as exc:
        raise HandoffError("lane ports must be decimal integers") from exc
    if any(port < 1024 or port > 65535 for port in ports) or len(set(ports)) != 3:
        raise HandoffError("lane ports must be distinct, unprivileged TCP ports")
    return Resources(values["foundation_instance"], *ports, values["postgres_db"], values["s3_bucket"])


def example_env(root: Path, resources: Resources) -> bytes:
    values: dict[str, str] = {}
    for line in (root / ".env.example").read_text(encoding="utf-8").splitlines():
        if not line or line.lstrip().startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator or key not in ENV_KEYS or key in values:
            raise HandoffError(".env.example has an unknown, malformed or duplicate assignment")
        values[key] = value
    if values.keys() != ENV_KEYS:
        raise HandoffError(".env.example is missing an expected local assignment")
    if not values["POSTGRES_PASSWORD"].startswith("local-disposable-") or not values["MINIO_ROOT_PASSWORD"].startswith("local-disposable-"):
        raise HandoffError(".env.example does not carry disposable local credentials")
    if values["S3_ACCESS_KEY_ID"] != values["MINIO_ROOT_USER"] or values["S3_SECRET_ACCESS_KEY"] != values["MINIO_ROOT_PASSWORD"]:
        raise HandoffError(".env.example's disposable S3 and MinIO identities disagree")
    values.update({
        "FOUNDATION_INSTANCE": resources.instance,
        "POSTGRES_DB": resources.database,
        "POSTGRES_PORT": str(resources.postgres_port),
        "S3_API_PORT": str(resources.s3_api_port),
        "S3_CONSOLE_PORT": str(resources.s3_console_port),
        "S3_BUCKET": resources.bucket,
        "S3_ENDPOINT_URL": f"http://127.0.0.1:{resources.s3_api_port}",
    })
    user = quote(values["POSTGRES_USER"], safe="")
    password = quote(values["POSTGRES_PASSWORD"], safe="")
    values["DATABASE_URL"] = f"postgresql+psycopg://{user}:{password}@127.0.0.1:{resources.postgres_port}/{resources.database}"
    return ("\n".join(f"{key}={values[key]}" for key in sorted(ENV_KEYS)) + "\n").encode()


def _existing_assignments(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if path.is_symlink():
        raise HandoffError(f"refusing symlinked lane environment: {path}")
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        if separator and key in {"FOUNDATION_INSTANCE", "POSTGRES_PORT", "S3_API_PORT", "S3_CONSOLE_PORT", "POSTGRES_DB", "S3_BUCKET"}:
            values[key] = value
    return values


def _check_other_lanes(root: Path, target: Path, resources: Resources) -> None:
    lanes = {env.parent.resolve() for env in (root / ".local/worktrees").glob("*/.env")}
    for line in _git_ok(root, "worktree", "list", "--porcelain").decode().splitlines():
        if line.startswith("worktree "):
            lanes.add(Path(line.removeprefix("worktree ")).resolve())
    lanes.discard(target.resolve())
    for lane in sorted(lanes):
        env = lane / ".env"
        if not env.exists() and not env.is_symlink():
            continue
        values = _existing_assignments(env)
        if values.get("FOUNDATION_INSTANCE") == resources.instance:
            raise HandoffError(f"instance already assigned to {lane}")
        if values.get("POSTGRES_DB") == resources.database:
            raise HandoffError(f"database already assigned to {lane}")
        if values.get("S3_BUCKET") == resources.bucket:
            raise HandoffError(f"bucket already assigned to {lane}")
        held = {values.get(key) for key in ("POSTGRES_PORT", "S3_API_PORT", "S3_CONSOLE_PORT")}
        for port in resources.ports:
            if str(port) in held:
                raise HandoffError(f"port {port} already assigned to {lane}")


def _check_free_ports(resources: Resources, proc_net: Path = Path("/proc/net")) -> None:
    """Read host-namespace listeners without opening a socket or touching a service."""
    listening: set[int] = set()
    for name in ("tcp", "tcp6"):
        path = proc_net / name
        try:
            lines = path.read_text(encoding="ascii").splitlines()
        except OSError as exc:
            raise HandoffError(f"cannot inspect listener table {path}: {exc}") from exc
        for line in lines[1:]:
            fields = line.split()
            if len(fields) < 4 or fields[3] != "0A":
                continue
            try:
                listening.add(int(fields[1].rsplit(":", 1)[1], 16))
            except (IndexError, ValueError) as exc:
                raise HandoffError(f"malformed listener row in {path}") from exc
    for port in resources.ports:
        if port in listening:
            raise HandoffError(f"TCP port {port} is already listening in this host namespace")


def _run(root: Path, argv: list[str]) -> None:
    result = subprocess.run(argv, cwd=root, check=False)
    if result.returncode:
        raise HandoffError(f"command failed (exit {result.returncode}): {' '.join(argv)}")


def prepare(root: Path, task_file: Path, *, dry_run: bool = False, install: bool = True,
            foundation_python: str | None = None, proc_net: Path = Path("/proc/net")) -> Path:
    root = root.resolve()
    task_file = task_file.resolve()
    if not task_file.is_relative_to(root) or task_file.parent != root / "docs/program/tasks":
        raise HandoffError("task file must be under this checkout's docs/program/tasks")
    _task_source(root, task_file)
    task = read_task(task_file)
    resources = read_resources(task_file)
    worktrees = root / ".local/worktrees"
    target = worktrees / task.task_id
    branch = f"agent/{task.task_id}"
    if git(root, "cat-file", "-e", f"{task.base}^{{commit}}").returncode:
        raise HandoffError("task base commit is unavailable")
    if git(root, "merge-base", "--is-ancestor", task.base, "HEAD").returncode:
        raise HandoffError("task base is not an ancestor of this checkout")
    env_bytes = example_env(root, resources)
    python: str | None = None
    if install:
        python = foundation_python or shutil.which("python3.12")
        if not python or not Path(python).is_file():
            raise HandoffError("Python 3.12 is required for bootstrap; pass --foundation-python")
        if not shutil.which("make") or not shutil.which("npm"):
            raise HandoffError("make and npm must be on PATH before lane installation")
    _check_other_lanes(root, target, resources)
    existing = target.exists()
    if existing:
        if target.is_symlink() or not (target / ".git").exists():
            raise HandoffError("target exists but is not a Git worktree")
        head = git(target, "rev-parse", "HEAD")
        current_branch = git(target, "branch", "--show-current")
        if head.returncode or head.stdout.decode().strip() != task.base or current_branch.stdout.decode().strip() != branch:
            raise HandoffError("existing worktree is not at the task's exact base and branch")
        status = git(target, "status", "--porcelain", "--untracked-files=all")
        if status.returncode or status.stdout:
            raise HandoffError("existing worktree is dirty")
        env_path = target / ".env"
        if env_path.is_symlink() or (env_path.exists() and env_path.read_bytes() != env_bytes):
            raise HandoffError("existing .env differs from the assigned disposable lane values")
    else:
        if git(root, "show-ref", "--verify", f"refs/heads/{branch}").returncode == 0:
            raise HandoffError("lane branch already exists without this worktree")
        _check_free_ports(resources, proc_net)
    print(f"task={task.task_id} base={task.base} branch={branch} worktree={target}")
    print(f"instance={resources.instance} ports={resources.ports} database={resources.database} bucket={resources.bucket}")
    if dry_run:
        print("DRY RUN: no worktree, .env or dependency change")
        return target
    if not existing:
        worktrees.mkdir(parents=True, exist_ok=True)
        _run(root, ["git", "worktree", "add", "-b", branch, str(target), task.base])
    env_path = target / ".env"
    if not env_path.exists():
        env_path.write_bytes(env_bytes)
        env_path.chmod(0o600)
    if install:
        assert python
        _run(target, ["make", "bootstrap", f"FOUNDATION_PYTHON={python}"])
        _run(target, ["npm", "--prefix", "web", "ci"])
    print("LANE READY" if install else "LANE PREPARED (dependencies not installed)")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-install", action="store_true", help="create only the isolated worktree and disposable .env")
    parser.add_argument("--foundation-python", help="absolute path to Python 3.12")
    args = parser.parse_args()
    try:
        prepare(Path(__file__).resolve().parents[1], args.task, dry_run=args.dry_run,
                install=not args.no_install, foundation_python=args.foundation_python)
        return 0
    except (HandoffError, OSError) as exc:
        print(f"LANE REFUSED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
