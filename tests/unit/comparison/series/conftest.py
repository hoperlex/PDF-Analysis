"""Shared fixtures of the series unit tests (`CMP-SERIES-01`).

The oracle is the synthetic corpus ``fixtures/comparison`` and its answer keys (authored next to the content, never
captured from this lane's output). A page profile is real: the same ceilinged child the product uses reads the page, and the
typed result is opened through the product's own reader. No database and no object store."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from auditmanager.comparison.profile import limits
from auditmanager.comparison.profile.models import PageProfileData, PageProfileRow
from auditmanager.comparison.profile.profiling import PageOutcome, profile_page
from auditmanager.comparison.profile.reader import PageProfileReader
from auditmanager.comparison.profile.runner import SubprocessChildRunner
from auditmanager.shared.identity import new_ulid
from auditmanager.storage.models import derive_blob_id

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "fixtures" / "comparison"


class _DictStore:
    def __init__(self) -> None:
        self.blobs: dict[str, bytes] = {}

    def put(self, data: bytes) -> str:
        blob_id = str(derive_blob_id(sha256=hashlib.sha256(data).hexdigest(), size=len(data)))
        self.blobs[blob_id] = data
        return blob_id

    def read(self, blob_id: Any, *, verify: bool = True) -> bytes:
        return self.blobs[str(blob_id)]


def _open(outcome: PageOutcome, *, version_uid: str, store: _DictStore, reader: PageProfileReader) -> PageProfileData:
    row = PageProfileRow(
        page_profile_id=f"cpr_{new_ulid()}", version_uid=version_uid, page_number=outcome.page_number,
        content_key=outcome.content_key, algo_version=limits.ALGO_VERSION, status=outcome.status, reason=outcome.reason,
        summary=outcome.summary, profile_blob_id=None if outcome.pack is None else store.put(outcome.pack),
        preview_blob_id=None, thumbnail_blob_id=None, created_at=datetime(2026, 10, 28, tzinfo=timezone.utc),
    )
    return reader.open_profile(row)


@pytest.fixture(scope="session")
def vs1_key() -> dict[str, Any]:
    return json.loads((FIXTURES / "vs1" / "answer_key.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def v4_first_page() -> PageProfileData:
    """Page 1 of the fourth version of VS-1: the sheet that carries the «Разрешение на внесение изменений» table."""
    store = _DictStore()
    reader = PageProfileReader(None, store)  # type: ignore[arg-type]
    path = FIXTURES / "vs1" / "v4.pdf"
    outcome = profile_page(
        SubprocessChildRunner(), pdf_path=str(path), page_index=0, version_sha256=hashlib.sha256(path.read_bytes()).hexdigest()
    )
    return _open(outcome, version_uid=f"ver_{new_ulid()}", store=store, reader=reader)
