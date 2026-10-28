"""Shared fixtures of the engine's unit tests (`CMP-ENGINE-01`).

The synthetic corpus ``fixtures/comparison`` and its answer keys are the oracle, authored next to the content that
creates each fact. Page profiles are built by the real children of `CMP-PROFILE-01` (once per session, a few seconds a
version) and the engine child is the real one, started the way the worker starts it; nothing here needs a database.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from auditmanager.comparison.engine.service import Computed, compute_pair
from auditmanager.comparison.profile.models import PageProfileData, PageProfileRow
from auditmanager.comparison.profile.profiling import PageOutcome, profile_page
from auditmanager.comparison.profile.reader import PageProfileReader
from auditmanager.comparison.profile.runner import SubprocessChildRunner

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "fixtures" / "comparison"


class _Page:
    """One page of a corpus version: its profile data and the PDF it came from."""

    def __init__(self, path: Path, number: int, outcome: PageOutcome) -> None:
        from datetime import datetime, timezone

        self.path = path
        self.number = number
        self.outcome = outcome
        row = PageProfileRow(
            page_profile_id="cpr_01ARZ3NDEKTSV4RRFFQ69G5FAV", version_uid="ver_01ARZ3NDEKTSV4RRFFQ69G5FAV",
            page_number=number, content_key=outcome.content_key, algo_version="cmp-profile/1", status=outcome.status,
            reason=outcome.reason, summary=outcome.summary, profile_blob_id="blob_unused", preview_blob_id=None,
            thumbnail_blob_id=None, created_at=datetime.now(timezone.utc))
        reader = PageProfileReader(None, None)  # type: ignore[arg-type]
        reader._blob = lambda blob_id: outcome.pack  # type: ignore[method-assign]
        self.row = row
        self.data: PageProfileData = reader.open_profile(row)


@pytest.fixture(scope="session")
def vs1_key() -> dict:
    return json.loads((FIXTURES / "vs1" / "answer_key.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def sp1_key() -> dict:
    return json.loads((FIXTURES / "sp1" / "answer_key.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def corpus_page() -> Callable[[str, int], _Page]:
    """``corpus_page("vs1/v2.pdf", 3)`` is page 3 of that file, profiled once."""
    runner = SubprocessChildRunner()
    cache: dict[tuple[str, int], _Page] = {}

    def get(relative: str, number: int) -> _Page:
        key = (relative, number)
        if key not in cache:
            path = FIXTURES / relative
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            outcome = profile_page(runner, pdf_path=str(path), page_index=number - 1, version_sha256=digest)
            cache[key] = _Page(path, number, outcome)
        return cache[key]

    return get


@pytest.fixture(scope="session")
def compare(corpus_page: Callable[[str, int], _Page]) -> Callable[..., Computed]:
    """``compare("vs1/v1.pdf", 2, "vs1/v2.pdf", 2)`` runs the engine's child on the two pages."""
    results: dict[tuple, Computed] = {}

    def run(a: str, pa: int, b: str, pb: int, *, reasons: tuple[str, ...] = (), part: str | None = None, **extra: Any) -> Computed:
        key = (a, pa, b, pb, reasons, part, tuple(sorted(extra)))
        if not extra and key in results:
            return results[key]
        page_a, page_b = corpus_page(a, pa), corpus_page(b, pb)
        computed = compute_pair(page_a.data, page_b.data, path_a=str(page_a.path), path_b=str(page_b.path),
                                link_reasons=reasons, part=part, **extra)
        if not extra:
            results[key] = computed
        return computed

    return run
