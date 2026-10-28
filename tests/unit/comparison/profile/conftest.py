"""Shared fixtures of the page-profile unit tests (`CMP-PROFILE-01`).

The synthetic corpus ``fixtures/comparison`` and its answer keys are the oracle: the keys are authored next to
the content that creates each fact, never captured from this lane's output, so a test that equals a profile
to its key is a test of the profile and not of itself. The children are real: a session-scoped run profiles
every page of the five VS-1 versions once (about thirty seconds, two children a page) and the tests read it.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from auditmanager.comparison.profile.profiling import PageOutcome, profile_page
from auditmanager.comparison.profile.runner import SubprocessChildRunner

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "fixtures" / "comparison"


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture(scope="session")
def vs1_key() -> dict:
    return json.loads((FIXTURES / "vs1" / "answer_key.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def sp1_key() -> dict:
    return json.loads((FIXTURES / "sp1" / "answer_key.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def runner() -> SubprocessChildRunner:
    return SubprocessChildRunner()


@pytest.fixture(scope="session")
def vs1_profiles(vs1_key: dict, runner: SubprocessChildRunner) -> dict[str, list[PageOutcome]]:
    """``{"V1": [outcome of page 1, ...], ...}``: every page of VS-1 through the real children."""
    profiles: dict[str, list[PageOutcome]] = {}
    for version in vs1_key["versions"]:
        path = FIXTURES / version["file"]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        profiles[version["id"]] = [
            profile_page(runner, pdf_path=str(path), page_index=index, version_sha256=digest)
            for index in range(version["page_count"])
        ]
    return profiles
