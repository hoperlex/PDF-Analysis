"""Fixtures for the replay suite, and the guard that keeps it offline.

``OD-13`` makes automated suites recorded-only. "Recorded-only" is worth nothing as an
intention, so it is enforced: :func:`_no_network` replaces the three socket entry
points every HTTP client in this tree reaches through, for every test in this suite.
``test_offline.py`` then proves the guard actually fires, because a guard nobody has
watched fail is a guard that may have been silently disabled.
"""

from __future__ import annotations

import json
import socket
from pathlib import Path
from typing import Any

import pytest

from auditmanager.analysis.text import RecordedAdapter

REPO_ROOT = Path(__file__).resolve().parents[3]
RECORDINGS = REPO_ROOT / "fixtures/recorded/text_analysis"
TEXT_LAYER = RECORDINGS / "inputs/ar_baseline_text_layer.json"
EXPECTED_ISSUES = REPO_ROOT / "fixtures/synthetic/ar/expected_issues.json"


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Refuse every socket. Autouse, so no test can opt out by forgetting."""

    def refuse(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("this suite must make no network call")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)


@pytest.fixture(scope="session")
def text_layer_document() -> dict[str, Any]:
    return json.loads(TEXT_LAYER.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def expected_issues() -> dict[str, Any]:
    return json.loads(EXPECTED_ISSUES.read_text(encoding="utf-8"))


@pytest.fixture()
def recorded_adapter() -> RecordedAdapter:
    return RecordedAdapter(RECORDINGS)


@pytest.fixture()
def variant_adapter() -> Any:
    """An adapter over one of the ``variants/`` directories."""

    def build(name: str) -> RecordedAdapter:
        return RecordedAdapter(RECORDINGS / "variants" / name)

    return build
