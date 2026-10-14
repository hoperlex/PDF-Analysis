"""GATE-PKG-01: the cleanup removes only what a finished lane left, and says why it keeps the rest.

Each KEEP rule below is a real way to destroy someone's work on this shared host: a dirty
or unmerged lane, a worktree another lane borrows its ``.venv`` from, a stack still
running, the persistent promotion database. Every rule has a case that would remove the
wrong thing if the rule were deleted.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "worktree_cleanup.py"

spec = importlib.util.spec_from_file_location("worktree_cleanup", SCRIPT)
assert spec and spec.loader
cleanup = importlib.util.module_from_spec(spec)
sys.modules["worktree_cleanup"] = cleanup
spec.loader.exec_module(cleanup)


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, check=True, text=True, capture_output=True).stdout.strip()


class FakeDocker:
    def __init__(self, containers=None, volumes=None, volume_users=None) -> None:
        self.containers = containers or {}
        self.volume_rows = volumes or []
        self.volume_users = volume_users or {}
        self.removed: list[str] = []

    def project_containers(self, project: str) -> list[str]:
        return self.containers.get(project, [])

    def volume_containers(self, volume: str) -> list[str]:
        return self.volume_users.get(volume, [])

    def volumes(self) -> list[tuple[str, str]]:
        return [row for row in self.volume_rows if row[0] not in self.removed]

    def remove_volume(self, volume: str) -> None:
        self.removed.append(volume)

    def disk_summary(self) -> str:
        return ""


def policy(**overrides) -> "cleanup.Policy":
    values = dict(merged_into=("dev",), idle_hours=0.0, keep=cleanup.DEFAULT_KEEP,
                  keep_instances=cleanup.DEFAULT_KEEP_INSTANCES, instance_prefixes=cleanup.DEFAULT_INSTANCE_PREFIXES)
    values.update(overrides)
    return cleanup.Policy(**values)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    main = tmp_path / "repo"
    main.mkdir()
    git(main, "init", "-q", "-b", "main")
    git(main, "config", "user.email", "c@example.test")
    git(main, "config", "user.name", "c")
    (main / ".gitignore").write_text(".local/\n.env\n/.venv\n", encoding="utf-8")
    git(main, "add", ".gitignore")
    git(main, "commit", "-q", "-m", "base")
    git(main, "branch", "dev")
    return main


def add_tree(repo: Path, name: str, branch: str, *, commit: bool = False) -> Path:
    path = repo / ".local" / "worktrees" / name
    git(repo, "worktree", "add", "-q", "-b", branch, str(path), "dev")
    if commit:
        (path / f"{name}.txt").write_text(name, encoding="utf-8")
        git(path, "add", ".")
        git(path, "commit", "-q", "-m", name)
    return path


def judge(repo: Path, docker=None, **overrides):
    trees = cleanup.list_worktrees(repo)
    verdicts = cleanup.judge_worktrees(repo, trees, policy(**overrides), docker=docker or FakeDocker(),
                                       now=time.time(), cwds=cleanup.process_cwds())
    return {Path(v.target).name: v for v in verdicts}


def test_a_merged_clean_idle_lane_is_removable_and_the_main_checkout_never_is(repo: Path) -> None:
    add_tree(repo, "lane-a", "agent/a")
    verdicts = judge(repo)
    assert verdicts["lane-a"].remove
    assert verdicts["repo"].reasons == ["the main checkout"]


def test_uncommitted_work_is_kept(repo: Path) -> None:
    path = add_tree(repo, "lane-dirty", "agent/dirty")
    (path / "draft.py").write_text("x = 1\n", encoding="utf-8")
    assert judge(repo)["lane-dirty"].reasons == ["1 uncommitted path(s)"]


def test_unmerged_commits_are_kept(repo: Path) -> None:
    add_tree(repo, "lane-new", "agent/new", commit=True)
    assert judge(repo)["lane-new"].reasons == ["HEAD not contained in dev"]


def test_plan_branches_and_named_globs_are_protected(repo: Path) -> None:
    add_tree(repo, "plan-x", "plan/x")
    add_tree(repo, "w55b-int", "integration/w55b")
    verdicts = judge(repo, keep=cleanup.DEFAULT_KEEP + ("w55b-*",))
    assert verdicts["plan-x"].reasons == ["protected by --keep plan/*"]
    assert verdicts["w55b-int"].reasons == ["protected by --keep w55b-*"]


def test_a_worktree_another_lane_borrows_its_venv_from_is_kept(repo: Path) -> None:
    provider = add_tree(repo, "w54-int", "integration/w54")
    (provider / ".venv").mkdir()
    borrower = add_tree(repo, "lane-b", "agent/b", commit=True)
    os.symlink(provider / ".venv", borrower / ".venv")
    assert judge(repo)["w54-int"].reasons == ["provides the .venv of lane-b"]


def test_recent_activity_is_kept(repo: Path) -> None:
    add_tree(repo, "lane-hot", "agent/hot")
    reasons = judge(repo, idle_hours=24.0)["lane-hot"].reasons
    assert len(reasons) == 1 and reasons[0].startswith("active 0.0 h ago")


def test_a_process_working_inside_is_kept(repo: Path) -> None:
    path = add_tree(repo, "lane-busy", "agent/busy")
    process = subprocess.Popen(["sleep", "60"], cwd=path)
    try:
        reasons = judge(repo)["lane-busy"].reasons
    finally:
        process.kill()
        process.wait()
    assert reasons == [f"process {process.pid} (sleep) has its cwd inside"]


def test_a_running_stack_is_kept_and_an_unreachable_docker_is_not_a_yes(repo: Path) -> None:
    path = add_tree(repo, "lane-stack", "agent/stack")
    (path / ".env").write_text("FOUNDATION_INSTANCE=gate-lane-stack\n", encoding="utf-8")
    running = FakeDocker(containers={"gate-lane-stack": ["gate-lane-stack-postgres-1 running"]})
    assert judge(repo, running)["lane-stack"].reasons == [
        "compose project gate-lane-stack has 1 container(s); run make down there"]

    class Broken(FakeDocker):
        def project_containers(self, project: str) -> list[str]:
            raise RuntimeError("docker ps failed: no daemon")
    reasons = judge(repo, Broken())["lane-stack"].reasons
    assert reasons == ["cannot tell whether compose project gate-lane-stack runs: docker ps failed: no daemon"]


def test_apply_removes_only_the_removable_worktrees_and_keeps_branches(repo: Path) -> None:
    gone = add_tree(repo, "lane-done", "agent/done")
    (gone / ".env").write_text("FOUNDATION_INSTANCE=gate-lane-done\n", encoding="utf-8")
    kept = add_tree(repo, "lane-open", "agent/open", commit=True)
    docker = FakeDocker(volumes=[("gate-lane-done-postgres-data", "gate-lane-done"),
                                 ("gate-lane-done-s3-data", "gate-lane-done")])
    trees = cleanup.list_worktrees(repo)
    verdicts = cleanup.judge_worktrees(repo, trees, policy(), docker=docker, now=time.time(), cwds=[])
    failures = cleanup.apply(repo, verdicts, docker, True, set(), lambda _line: None)
    assert failures == 0
    assert not gone.exists() and kept.exists()
    assert "agent/done" in git(repo, "branch", "--list", "agent/done")
    assert docker.removed == ["gate-lane-done-postgres-data", "gate-lane-done-s3-data"]


def test_orphan_volumes_need_the_signature_no_container_and_no_live_instance() -> None:
    docker = FakeDocker(
        volumes=[
            ("gate-w52r-postgres-data", "gate-w52r"),
            ("gate-w52r-s3-data", "gate-w52r"),
            ("auditmanager-promotion-postgres-data", "auditmanager-promotion"),
            ("auditmanager-w55b-fix-postgres-data", "auditmanager-w55b-fix"),
            ("auditmanager-w19a-postgres-data", "auditmanager-w19a"),
            ("technic-dev_pgdata", "technic-dev"),
            ("gate-odd-cache", "gate-odd"),
            ("gate-busy-s3-data", "gate-busy"),
            ("3f2a9c", ""),
        ],
        containers={"auditmanager-w19a": ["auditmanager-w19a-api-1 running"]},
        volume_users={"gate-busy-s3-data": ["something-1"]},
    )
    verdicts = {v.target: v for v in cleanup.judge_volumes(docker, policy(), {"auditmanager-w55b-fix"})}
    assert set(verdicts) == {
        "gate-w52r-postgres-data", "gate-w52r-s3-data", "auditmanager-promotion-postgres-data",
        "auditmanager-w55b-fix-postgres-data", "auditmanager-w19a-postgres-data", "gate-busy-s3-data",
    }
    assert verdicts["gate-w52r-postgres-data"].remove and verdicts["gate-w52r-s3-data"].remove
    assert verdicts["auditmanager-promotion-postgres-data"].reasons == ["protected instance"]
    assert verdicts["auditmanager-w55b-fix-postgres-data"].reasons == ["a worktree's .env still names this instance"]
    assert verdicts["auditmanager-w19a-postgres-data"].reasons == ["1 container(s) of the project exist"]
    assert verdicts["gate-busy-s3-data"].reasons == ["used by something-1"]


def make_copy(home: Path, name: str, *, marker: bool = True, git_dir: bool = False) -> Path:
    path = home / name
    (path / "src" / "auditmanager").mkdir(parents=True)
    (path / "pyproject.toml").write_text(
        'name = "auditmanager-foundation"\n' if marker else 'name = "other"\n', encoding="utf-8")
    if git_dir:
        (path / ".git").mkdir()
    return path


def test_mutation_copies_need_the_marker_and_rmtree_does_not_follow_links(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    precious = tmp_path / "worktree-docs"
    precious.mkdir()
    (precious / "keep.md").write_text("evidence", encoding="utf-8")
    copy = make_copy(home, "w10api-mut")
    os.symlink(precious, copy / "docs")
    make_copy(home, "other-mut", marker=False)
    make_copy(home, "clone-mut", git_dir=True)
    verdicts = cleanup.judge_mutation_copies(home, policy(), now=time.time(), cwds=[])
    assert {Path(v.target).name: v.remove for v in verdicts} == {
        "w10api-mut": True, "other-mut": False, "clone-mut": False}
    failures = cleanup.apply(tmp_path, verdicts, FakeDocker(), False, set(), lambda _line: None)
    assert not copy.exists()
    assert (precious / "keep.md").read_text(encoding="utf-8") == "evidence"
    assert failures <= 1  # tmp_path is no git repository, so the final prune may fail


def test_the_report_changes_nothing(repo: Path, tmp_path: Path) -> None:
    lane = add_tree(repo, "lane-done", "agent/done")
    home = tmp_path / "home"
    copy = make_copy(home, "w1-mut")
    before = git(repo, "worktree", "list", "--porcelain")
    result = subprocess.run([sys.executable, str(SCRIPT), "--repo", str(repo), "--home", str(home),
                             "--merged-into", "dev", "--idle-hours", "0", "--mutation-copies"],
                            text=True, capture_output=True, timeout=300)
    assert result.returncode == 0, result.stderr
    assert f"REMOVE {lane}" in result.stdout and f"REMOVE {copy}" in result.stdout
    assert "DRY RUN: 2 item(s) marked REMOVE. Nothing was changed" in result.stdout
    assert git(repo, "worktree", "list", "--porcelain") == before
    assert lane.is_dir() and copy.is_dir()
