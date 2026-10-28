"""Shared fixtures of the matrix unit tests (`CMP-MATRIX-01`).

The oracle is the synthetic corpus ``fixtures/comparison`` and its answer key ``sheet_identity`` (authored next to
the content, never captured from this lane's output). The profiles are real: a session-scoped run puts every page
of the five VS-1 versions and the SP-1 pair through the same ceilinged children the product uses (about thirty
seconds), and the tests read the typed result. No database and no object store: the archive is opened through the
reader the product uses, with a dictionary for a store.
"""

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


def profile_data(outcome: PageOutcome, *, version_uid: str, store: _DictStore, reader: PageProfileReader) -> PageProfileData:
    """The typed profile of one page, opened through the product's own reader."""
    row = PageProfileRow(
        page_profile_id=f"cpr_{new_ulid()}",
        version_uid=version_uid,
        page_number=outcome.page_number,
        content_key=outcome.content_key,
        algo_version=limits.ALGO_VERSION,
        status=outcome.status,
        reason=outcome.reason,
        summary=outcome.summary,
        profile_blob_id=None if outcome.pack is None else store.put(outcome.pack),
        preview_blob_id=None,
        thumbnail_blob_id=None,
        created_at=datetime(2026, 10, 28, tzinfo=timezone.utc),
    )
    return reader.open_profile(row)


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture(scope="session")
def vs1_key() -> dict[str, Any]:
    return json.loads((FIXTURES / "vs1" / "answer_key.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def sp1_key() -> dict[str, Any]:
    return json.loads((FIXTURES / "sp1" / "answer_key.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def profile_reader() -> tuple[PageProfileReader, _DictStore]:
    store = _DictStore()
    return PageProfileReader(None, store), store  # type: ignore[arg-type]


@pytest.fixture(scope="session")
def vs1(vs1_key: dict[str, Any], profile_reader: tuple[PageProfileReader, _DictStore]) -> dict[str, Any]:
    """``{"versions": {"V1": ("ver_...", [PageProfileData, ...]), ...}, "order": ["V1", ...]}``: VS-1 through the
    real children."""
    reader, store = profile_reader
    runner = SubprocessChildRunner()
    versions: dict[str, tuple[str, list[PageProfileData]]] = {}
    for version in vs1_key["versions"]:
        path = FIXTURES / version["file"]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        version_uid = f"ver_{new_ulid()}"
        pages = [
            profile_data(
                profile_page(runner, pdf_path=str(path), page_index=index, version_sha256=digest),
                version_uid=version_uid, store=store, reader=reader,
            )
            for index in range(version["page_count"])
        ]
        versions[version["id"]] = (version_uid, pages)
    return {"versions": versions, "order": [v["id"] for v in vs1_key["versions"]]}
