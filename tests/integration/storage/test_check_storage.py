"""The ``check-storage`` provider, exercised the way ``make`` invokes it.

``FOUNDATION_LOCK.json`` records the invocation and the contract around it: the
sentinel must be the last actual output line, and a zero exit without it is
refused. Both halves are asserted here so a regression is caught by this lane's
own suite rather than at Gate A convergence.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from auditmanager.storage import S3StorageSettings
from auditmanager.storage.check import SENTINEL
from auditmanager.storage.settings import REQUIRED_VARS

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _run_check(settings: S3StorageSettings, **overrides: str) -> subprocess.CompletedProcess:
    environment = dict(os.environ)
    environment.update(
        {
            "PYTHONPATH": "src",
            "S3_ENDPOINT_URL": settings.endpoint_url,
            "S3_REGION": settings.region,
            "S3_ACCESS_KEY_ID": settings.access_key_id,
            "S3_SECRET_ACCESS_KEY": settings.secret_access_key,
            "S3_BUCKET": settings.bucket,
        }
    )
    environment.update(overrides)
    return subprocess.run(
        [sys.executable, "-m", "auditmanager.storage.check"],
        cwd=REPOSITORY_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=180,
    )


def test_check_storage_exits_zero_with_the_sentinel_last(
    settings: S3StorageSettings,
) -> None:
    result = _run_check(settings)
    assert result.returncode == 0, result.stderr
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    assert lines[-1] == SENTINEL
    assert lines.count(SENTINEL) == 1


def test_check_storage_output_names_no_bucket_and_no_key(
    settings: S3StorageSettings,
) -> None:
    result = _run_check(settings)
    combined = result.stdout + result.stderr
    assert settings.bucket not in combined
    assert settings.secret_access_key not in combined
    assert "blobs/" not in combined
    assert "temporary/" not in combined


def test_check_storage_leaves_nothing_behind(
    settings: S3StorageSettings, bucket_keys: Any
) -> None:
    before = bucket_keys()
    result = _run_check(settings)
    assert result.returncode == 0, result.stderr
    assert bucket_keys() == before


def test_check_storage_fails_without_credentials(settings: S3StorageSettings) -> None:
    """The guard proving the check can actually fail.

    A check that cannot fail is not evidence. Pointed at the same bucket with
    a refused key, it must exit non-zero and must not print the sentinel.
    """
    result = _run_check(
        settings,
        S3_ACCESS_KEY_ID="a3-wrong-access-key",
        S3_SECRET_ACCESS_KEY="a3-wrong-secret-key",
    )
    assert result.returncode != 0
    assert SENTINEL not in result.stdout
    assert "check-storage failed" in result.stderr


def test_check_storage_fails_when_the_store_is_unreachable(
    settings: S3StorageSettings,
) -> None:
    result = _run_check(settings, S3_ENDPOINT_URL="http://127.0.0.1:59099")
    assert result.returncode != 0
    assert SENTINEL not in result.stdout
    assert "dependency_unavailable" in result.stderr


def test_check_storage_fails_when_a_frozen_variable_is_missing(
    settings: S3StorageSettings,
) -> None:
    result = _run_check(settings, S3_BUCKET="")
    assert result.returncode != 0
    assert SENTINEL not in result.stdout
    assert "S3_BUCKET" in result.stderr


def test_the_check_consumes_only_the_frozen_environment_names() -> None:
    assert set(REQUIRED_VARS) == {
        "S3_ENDPOINT_URL",
        "S3_REGION",
        "S3_ACCESS_KEY_ID",
        "S3_SECRET_ACCESS_KEY",
        "S3_BUCKET",
    }
