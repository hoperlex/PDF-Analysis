"""The operator commands, run as the operator runs them: ``python -m auditmanager.norms.embedding``."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from auditmanager.norms.embedding.builder import run_build
from auditmanager.norms.embedding.checkpoint import prepare_plan
from tests.integration.norms.embedding.support import (
    CHUNKING_PROFILE,
    ROOT,
    SNAPSHOT_ID,
    FakeEncoder,
    chunk_set,
    identity,
)


def _command(*arguments: str, environment: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "auditmanager.norms.embedding", *arguments],
        cwd=ROOT,
        env={"PATH": "/usr/bin:/bin", "PYTHONPATH": str(ROOT / "src"), **(environment or {})},
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def test_status_counts_verified_missing_and_invalid_batches(tmp_path: Path) -> None:
    directory = tmp_path / "build"
    prepare_plan(directory, identity(), chunk_set(12), batch_chunks=4)
    run_build(
        directory, FakeEncoder(), norms_snapshot_id=SNAPSHOT_ID, chunking_profile=CHUNKING_PROFILE,
        max_batches=2, report=lambda _line: None,
    )
    (directory / "vectors" / "batch-00001.jsonl.sha256").unlink()
    completed = _command("status", "--checkpoint", str(directory))
    assert completed.returncode == 0, completed.stderr
    lines = completed.stdout.splitlines()
    assert lines[0].startswith("batch 1: invalid (batch-00001.jsonl has no SHA-256 sidecar")
    report = json.loads("\n".join(lines[1:]))
    assert (report["batches"], report["verified"], report["invalid"], report["missing"]) == (3, 1, 1, 1)


def test_build_refuses_outside_the_image_before_touching_the_directory(tmp_path: Path) -> None:
    directory = tmp_path / "build"
    prepare_plan(directory, identity(), chunk_set(4), batch_chunks=4)
    completed = _command(
        "build", "--snapshot", SNAPSHOT_ID, "--chunking-profile", CHUNKING_PROFILE,
        "--checkpoint", str(directory),
    )
    assert completed.returncode == 2
    assert "refused: HF_HUB_OFFLINE must be '1'" in completed.stderr
    assert not (directory / "vectors").exists()


def test_a_malformed_snapshot_id_and_a_missing_plan_are_refused(tmp_path: Path) -> None:
    completed = _command("build", "--snapshot", "ns_short", "--chunking-profile", CHUNKING_PROFILE, "--checkpoint", str(tmp_path))
    assert completed.returncode == 2 and "is not a norms snapshot id" in completed.stderr
    completed = _command("status", "--checkpoint", str(tmp_path / "absent"))
    assert completed.returncode == 2 and "run prepare first" in completed.stderr
