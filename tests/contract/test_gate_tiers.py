"""Exercise the real Make targets with controlled commands and no Docker daemon."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def checkout(tmp_path: Path) -> Path:
    shutil.copy2(ROOT / "Makefile", tmp_path / "Makefile")
    python = tmp_path / ".venv/bin/python"
    python.parent.mkdir(parents=True)
    python.write_text("#!/bin/sh\nexit \"${FAKE_PY_EXIT:-0}\"\n", encoding="utf-8")
    python.chmod(0o755)
    npm = tmp_path / "bin/npm"
    npm.parent.mkdir()
    npm.write_text("#!/bin/sh\nexit \"${FAKE_NPM_EXIT:-0}\"\n", encoding="utf-8")
    npm.chmod(0o755)
    (tmp_path / "web/node_modules").mkdir(parents=True)
    unit = tmp_path / "tests/unit/test_probe.py"
    unit.parent.mkdir(parents=True)
    unit.write_text("def test_probe(): pass\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    return tmp_path


def make(checkout: Path, target: str, **variables: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PATH"] = f"{checkout / 'bin'}:{env['PATH']}"
    env.update(variables)
    return subprocess.run(["make", target], cwd=checkout, env=env, text=True, capture_output=True)


def test_fast_success_has_only_its_own_marker(checkout: Path) -> None:
    result = make(checkout, "gate-fast")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "GATE FAST OK:" in result.stdout
    assert "GATE OK:" not in result.stdout


@pytest.mark.parametrize("variable,value", [("FAKE_NPM_EXIT", "4"), ("FAKE_PY_EXIT", "5")])
def test_fast_failed_check_never_prints_success(
    checkout: Path, variable: str, value: str
) -> None:
    result = make(checkout, "gate-fast", **{variable: value})
    assert result.returncode != 0
    assert "GATE FAST OK:" not in result.stdout


def test_affected_delegates_to_light_acceptance_and_propagates_failure(checkout: Path) -> None:
    success = make(checkout, "gate-affected")
    assert success.returncode == 0, success.stdout + success.stderr
    assert "GATE AFFECTED OK:" in success.stdout
    assert "GATE OK:" not in success.stdout
    failure = make(checkout, "gate-affected", FAKE_PY_EXIT="6")
    assert failure.returncode != 0
    assert "GATE AFFECTED OK:" not in failure.stdout


def test_stage_timer_reports_failure_without_changing_status(checkout: Path) -> None:
    failure = make(checkout, "gate-preflight", FAKE_PY_EXIT="7")
    assert failure.returncode != 0
    assert "GATE TIMING preflight " in failure.stderr
    assert "exit=7" in failure.stderr
    assert "GATE OK:" not in failure.stdout
    success = make(checkout, "gate-preflight")
    assert success.returncode == 0, success.stdout + success.stderr
    assert "GATE TIMING preflight " in success.stderr
    assert "exit=0" in success.stderr


def test_complete_gate_keeps_its_graph_and_reports_slowest_python_tests() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "gate: gate-preflight gate-slot gate-static foundation\n" in makefile
    assert makefile.count("--durations=20") >= 5  # foundation, first/rest battery, contract, fast
    assert makefile.count('"GATE OK: battery, foundation, frontend lint/typecheck/tests and whitespace all pass"') == 1
