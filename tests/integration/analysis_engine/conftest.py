"""Fixtures for the stage-engine suite, run against real PostgreSQL and MinIO.

Nothing here is mocked and nothing is skipped when a service is absent: a skip would
let the negative paths - the ones that prove the guards can fire - pass by not running.
If the service or its configuration is missing, collection fails loudly.

Configuration comes from the frozen ``FF-01`` section 3 environment names. A literal
``.venv/bin/pytest tests/integration/analysis_engine`` is the documented gate command,
so when those names are not already exported the session reads them out of the
repository-root ``.env`` - the same git-ignored file ``make`` reads - without
overriding anything the caller set.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterator

import pytest

from auditmanager.storage import (
    S3BlobStore,
    S3StorageSettings,
    StorageError,
    sha256_of,
)
from auditmanager.storage.models import ROLE_SOURCE_DOCUMENT
from auditmanager.storage.settings import REQUIRED_VARS

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CORPUS = REPOSITORY_ROOT / "fixtures" / "synthetic" / "ar"
BASELINE_PDF = CORPUS / "ar_baseline.pdf"
EXPECTED_ISSUES = CORPUS / "expected_issues.json"

#: A well-formed ``DocumentVersion`` identity. The stages take it as a parameter; they
#: never allocate one, because identity allocation is not this seam's business.
VERSION_UID = "ver_01M2545JSD15ETSNNV904X991J"


def _load_dotenv_if_needed() -> None:
    """Fill in missing frozen names from the repository-root ``.env``.

    Deliberately narrow: only the names the storage adapter requires, never overriding
    an exported value, and no shell evaluation - the file is data. This is not a
    general dotenv loader and must not grow into one.
    """
    if all(os.environ.get(name) for name in REQUIRED_VARS):
        return
    dotenv = REPOSITORY_ROOT / ".env"
    if not dotenv.is_file():
        return
    for raw in dotenv.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        name, sep, value = line.partition("=")
        if not sep:
            continue
        name = name.strip()
        if name not in REQUIRED_VARS or os.environ.get(name):
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ[name] = value


@pytest.fixture(scope="session")
def store() -> S3BlobStore:
    _load_dotenv_if_needed()
    try:
        settings = S3StorageSettings.from_env()
    except StorageError as exc:
        pytest.fail(
            "tests/integration/analysis_engine needs a real S3-compatible service. "
            f"{exc} Export the FF-01 section 3 S3_* names, or create .env."
        )
    blob_store = S3BlobStore(settings)
    try:
        blob_store.check_access()
    except StorageError as exc:
        pytest.fail(
            "the configured private bucket is not reachable with the configured "
            f"application credentials: {exc}"
        )
    return blob_store


@pytest.fixture(scope="session")
def database_url() -> str:
    """The suite runs against a real database as well as a real object store.

    It is required rather than optional: the gate command names PostgreSQL, and a
    suite that quietly ran without it would be weaker evidence than it claims to be.
    """
    _load_dotenv_if_needed()
    url = os.environ.get("DATABASE_URL")
    if not url:
        dotenv = REPOSITORY_ROOT / ".env"
        if dotenv.is_file():
            for raw in dotenv.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if line.startswith("DATABASE_URL="):
                    url = line.partition("=")[2].strip()
                    os.environ.setdefault("DATABASE_URL", url)
                    break
    if not url:
        pytest.fail(
            "DATABASE_URL is not configured. This suite runs against real "
            "PostgreSQL; it does not skip. Create .env or export the name."
        )
    return url


@pytest.fixture(scope="session")
def baseline_pdf() -> bytes:
    return BASELINE_PDF.read_bytes()


@pytest.fixture(scope="session")
def source_blob(store: S3BlobStore, baseline_pdf: bytes) -> Any:
    """The baseline corpus PDF, published once for the whole session."""
    published = store.put_blob(
        baseline_pdf,
        declared_sha256=sha256_of(baseline_pdf),
        declared_size=len(baseline_pdf),
        role=ROLE_SOURCE_DOCUMENT,
        media_type="application/pdf",
    )
    return published.blob_id


@pytest.fixture(scope="session")
def manifest() -> dict[str, Any]:
    return json.loads(EXPECTED_ISSUES.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def manifest_anchors(manifest: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    """Every quotation the manifest anchors to a page and a page-local offset.

    Twelve of them: five seeded-issue evidence items and seven control anchors. They
    are collected by *shape* - a mapping carrying ``page``, ``quotation`` and
    ``char_offset_in_page_text`` - rather than by a hard-coded path, so a manifest
    that grows another anchor is covered without editing this fixture.
    """
    found: list[dict[str, Any]] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if {"page", "quotation", "char_offset_in_page_text"} <= node.keys():
                found.append(node)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(manifest)
    return tuple(found)
