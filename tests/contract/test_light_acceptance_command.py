"""Synthetic R-70 diffs; no live stand or suite is invoked by these selector tests."""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("light_acceptance", ROOT / "scripts/light_acceptance.py")
assert SPEC and SPEC.loader
light = importlib.util.module_from_spec(SPEC)
import sys

sys.modules[SPEC.name] = light
SPEC.loader.exec_module(light)


def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=True)
    return result.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "light@example.invalid")
    git(tmp_path, "config", "user.name", "Light Acceptance Test")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "note.md").write_text("base\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "base")
    monkeypatch.setattr(light, "ROOT", tmp_path)
    return tmp_path


def commit_path(repo: Path, path: str) -> str:
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("changed\n")
    git(repo, "add", path)
    git(repo, "commit", "-qm", f"change {path}")
    return git(repo, "rev-parse", "HEAD")


def test_docs_only_diff_needs_only_common_checks(repo: Path) -> None:
    base = git(repo, "rev-parse", "HEAD")
    commit_path(repo, "docs/more.md")
    assert light.classify(light.changed_paths(base)) == light.Selection((), False)


def test_backend_context_selects_its_exercising_suite(repo: Path) -> None:
    base = git(repo, "rev-parse", "HEAD")
    suite = repo / "tests/integration/runs"
    suite.mkdir(parents=True)
    (suite / "test_run.py").write_text("def test_run(): pass\n")
    target = repo / "src/auditmanager/runs/worker.py"
    target.parent.mkdir(parents=True)
    target.write_text("changed\n")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "change runs")
    assert light.classify(light.changed_paths(base)) == light.Selection(("runs",), False)


@pytest.mark.parametrize(("path", "expected"), [
    ("src/auditmanager/workers/service.py", ("jobs", "runs", "workers")),
    ("src/auditmanager/execution/public.py", ("api", "execution", "runs")),
    ("src/auditmanager/jobs/repository.py", ("jobs", "runs")),
])
def test_execution_contexts_select_their_suites(
    repo: Path, path: str, expected: tuple[str, ...]
) -> None:
    """`W54-WORKER-01`: the worker, execution and jobs contexts are mapped, not unknown."""
    for suite in expected:
        directory = repo / "tests/integration" / suite
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "test_it.py").write_text("def test_it(): pass\n")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "suites")
    base = git(repo, "rev-parse", "HEAD")
    commit_path(repo, path)
    assert light.classify(light.changed_paths(base)) == light.Selection(expected, False)


def test_the_real_execution_suites_exist() -> None:
    """The mapping names suites this repository really has; an empty one is refused."""
    for context in ("workers", "execution", "jobs"):
        for suite in light.CONTEXT_SUITES[context]:
            directory = ROOT / "tests" / "integration" / suite
            assert any(directory.rglob("test_*.py")), f"{directory} has no tests"


@pytest.mark.parametrize("path", [
    "web/src/_pages/dashboard/ui/page.tsx",
    "web/src/app/bff/session/screen-lock.ts",
    "web/src/app/bff/v1/[...path]/route.ts",
])
def test_screen_diff_selects_live_journey(repo: Path, path: str) -> None:
    base = git(repo, "rev-parse", "HEAD")
    commit_path(repo, path)
    assert light.classify(light.changed_paths(base)) == light.Selection((), True)


def test_risk_diff_requires_full_gate_and_cannot_substitute_light(repo: Path) -> None:
    base = git(repo, "rev-parse", "HEAD")
    commit_path(repo, "Makefile")
    with pytest.raises(light.SelectionError, match=r"complete make gate required.*Makefile"):
        light.classify(light.changed_paths(base))
    makefile = (ROOT / "Makefile").read_text()
    # GATE-PKG-01: the complete gate keeps every component; only their order moved, so the
    # cheap refusals and the container-free reds come before the containers and the battery.
    assert "gate: gate-preflight gate-slot gate-static foundation\n" in makefile
    assert "check_whitespace\n\trun_frontend\n\tload_env\n\trequire_env_coherence\n\trun_contract" in makefile
    assert "run_battery\n\tgate_memory_report\n" in makefile
    assert '"GATE OK: battery, foundation, frontend lint/typecheck/tests and whitespace all pass"' in makefile


@pytest.mark.parametrize("path,description", [
    ("src/auditmanager/new_context/handler.py", "backend context new_context"),
    ("web/src/new_layer/page.tsx", "screen-affecting path"),
])
def test_unknown_context_or_screen_fails_closed(repo: Path, path: str, description: str) -> None:
    base = git(repo, "rev-parse", "HEAD")
    commit_path(repo, path)
    with pytest.raises(light.SelectionError, match=description):
        light.classify(light.changed_paths(base))


def test_missing_nonancestor_and_dirty_base_are_refused(repo: Path) -> None:
    with pytest.raises(light.SelectionError, match="full 40-hex"):
        light.changed_paths("")
    base = git(repo, "rev-parse", "HEAD")
    commit_path(repo, "docs/more.md")
    with pytest.raises(light.SelectionError, match="not an ancestor"):
        _nonancestor(repo)
    (repo / "docs" / "scratch.md").write_text("untracked\n")
    with pytest.raises(light.SelectionError, match="dirty"):
        light.changed_paths(base)


def _nonancestor(repo: Path) -> None:
    # A valid commit that cannot be an ancestor of the current branch.
    head = git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "-qb", "other", "HEAD~1")
    commit_path(repo, "docs/other.md")
    other = git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "-q", head)
    light.changed_paths(other)
