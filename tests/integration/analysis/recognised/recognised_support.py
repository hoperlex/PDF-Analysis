"""Shared helpers for the recognised-text suite (`W55B-RECOGNISED-01`). Not a test module.

The committed portal bundles are opened with the product's own archive reader
(``auditmanager.ingest.bundle_archive.extract_bundle``, the extract helper every ingest test
uses), never with hand-typed member bytes. The seeded OCR defects come from the bundles'
own manifest, ``fixtures/synthetic/ar/bundles/bundle_manifest.json``, written by the
committed builder ``tools/fixtures/build_portal_bundles.py``.

The services this suite needs (the S3-compatible store; the run-wiring module needs
PostgreSQL too) are real and never skipped: a missing service fails the session, as in
``tests/integration/analysis_engine``. The store fixture is bound into each test module
that uses it (``store = recognised_support.store``) rather than declared in a
``conftest.py``.
"""

from __future__ import annotations

import io
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from auditmanager.ingest.bundle_archive import (
    ROLE_BLOCKS,
    ROLE_PDF,
    ROLE_RESULTS_MD,
    extract_bundle,
)
from auditmanager.storage import S3BlobStore, S3StorageSettings, StorageError, sha256_of
from auditmanager.storage.settings import REQUIRED_VARS

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
CORPUS = REPOSITORY_ROOT / "fixtures" / "synthetic" / "ar"
BUNDLES = CORPUS / "bundles"
BUNDLE_MANIFEST = BUNDLES / "bundle_manifest.json"

#: A well-formed ``DocumentVersion`` identity; the stage takes it, it never allocates one.
VERSION_UID = "ver_01M2545JSD15ETSNNV904X991J"

#: The seeded defect kinds of the bundle manifest, and the flag each must raise.
FLAG_FOR_KIND = {
    "latin_homoglyph": "homoglyph",
    "cjk_character": "cjk",
    "doubled_list_marker": "doubled_list_marker",
    "mixed_script_word": "mixed_script",
}


@dataclass(frozen=True, slots=True)
class BundleMembers:
    """The three members ``source_preparation`` reads, as the archive holds them."""

    name: str
    pdf: bytes
    markdown: bytes
    block_list: bytes

    @property
    def blocks(self) -> list[dict[str, Any]]:
        return list(json.loads(self.block_list)["blocks"])


def manifest() -> dict[str, Any]:
    return json.loads(BUNDLE_MANIFEST.read_text(encoding="utf-8"))


def manifest_entry(name: str) -> dict[str, Any]:
    return next(entry for entry in manifest()["bundles"] if entry["file"] == name)


def committed_names() -> list[str]:
    """Every committed bundle the manifest lists, in its order."""
    return [entry["file"] for entry in manifest()["bundles"]]


def members(name: str) -> BundleMembers:
    """One committed bundle's members, read through the product's archive reader."""
    with extract_bundle(io.BytesIO((BUNDLES / name).read_bytes())) as bundle:
        return BundleMembers(
            name=name,
            pdf=bundle.read_bytes(ROLE_PDF),
            markdown=bundle.read_bytes(ROLE_RESULTS_MD),
            block_list=bundle.read_bytes(ROLE_BLOCKS),
        )


def _load_dotenv_if_needed() -> None:
    """The frozen names from the repository-root ``.env`` when not exported (data, not shell)."""
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
        name = name.strip()
        if not sep or name not in REQUIRED_VARS or os.environ.get(name):
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ[name] = value


@pytest.fixture(scope="session")
def store() -> S3BlobStore:
    """The lane's real S3-compatible store; absent, the session fails rather than skips."""
    _load_dotenv_if_needed()
    try:
        settings = S3StorageSettings.from_env()
    except StorageError as exc:
        pytest.fail(f"this suite needs a real S3-compatible service. {exc}")
    blob_store = S3BlobStore(settings)
    try:
        blob_store.check_access()
    except StorageError as exc:
        pytest.fail(f"the configured private bucket is not reachable: {exc}")
    return blob_store


def publish(store: Any, payload: bytes, *, role: str, media_type: str) -> Any:
    """Publish ``payload`` under a blob role and return its ``blob_id``."""
    return store.put_blob(
        payload,
        declared_sha256=sha256_of(payload),
        declared_size=len(payload),
        role=role,
        media_type=media_type,
    ).blob_id


def stage_inputs(
    store: Any,
    pdf: bytes,
    *,
    markdown: bytes | None = None,
    block_list: bytes | None = None,
) -> dict[str, Any]:
    """``source_preparation``'s inputs by contract role; the two bundle members optional."""
    from auditmanager.analysis.public import (
        ROLE_SOURCE_DOCUMENT,
        ROLE_SOURCE_MARKDOWN,
        ROLE_SOURCE_STRUCTURED_COMPANION,
    )

    inputs = {
        ROLE_SOURCE_DOCUMENT: publish(
            store, pdf, role="source_document", media_type="application/pdf"
        )
    }
    if markdown is not None:
        inputs[ROLE_SOURCE_MARKDOWN] = publish(
            store, markdown, role="source_markdown", media_type="text/markdown"
        )
    if block_list is not None:
        inputs[ROLE_SOURCE_STRUCTURED_COMPANION] = publish(
            store,
            block_list,
            role="source_structured_companion",
            media_type="application/json",
        )
    return inputs


def bundle_inputs(store: Any, bundle: BundleMembers) -> dict[str, Any]:
    return stage_inputs(
        store, bundle.pdf, markdown=bundle.markdown, block_list=bundle.block_list
    )


#: The keys of each entry kind, exactly (``P02_SEAMS`` section 4.8).
RECOGNISED_ENTRY_KEYS = frozenset(
    {"portal_block_id", "page_number", "kind", "quote_source", "text", "flags"}
)
DESCRIPTION_ENTRY_KEYS = frozenset({"portal_block_id", "page_number", "kind", "text"})
ROOT_KEYS = frozenset(
    {"artifact_role", "artifact_version", "version_uid", "results_sha256", "entries"}
)


def assert_recognised_text_shape(
    document: Any, *, version_uid: str, markdown: bytes, page_count: int
) -> None:
    """A strict structural validator of ``prepared.recognised_text`` (section 4.8).

    Written here because the stage-result and artifact contracts carry no JSON schema for
    this role. Every literal is the seam's, not the module's.
    """
    import hashlib
    import re

    assert isinstance(document, dict)
    assert set(document) == ROOT_KEYS, sorted(document)
    assert document["artifact_role"] == "prepared.recognised_text"
    assert document["artifact_version"] == "1.0.0"
    assert document["version_uid"] == version_uid
    assert document["results_sha256"] == hashlib.sha256(markdown).hexdigest()
    entries = document["entries"]
    assert isinstance(entries, list)
    flag_pattern = re.compile(r"[a-z][a-z0-9_]{0,63}")
    keys_seen: list[tuple[int, str]] = []
    for entry in entries:
        assert isinstance(entry, dict)
        assert re.fullmatch(r"blk_[0-9a-f]{32}", entry["portal_block_id"])
        assert isinstance(entry["page_number"], int) and not isinstance(entry["page_number"], bool)
        assert 1 <= entry["page_number"] <= page_count
        assert isinstance(entry["text"], str)
        for forbidden in ("char_start", "char_end", "offset", "offsets", "block_id"):
            assert forbidden not in entry, f"an entry carries {forbidden!r}"
        if entry["kind"] == "recognised_text":
            assert set(entry) == RECOGNISED_ENTRY_KEYS, sorted(entry)
            assert entry["quote_source"] == "recognised"
            flags = entry["flags"]
            assert isinstance(flags, list)
            assert all(isinstance(f, str) and flag_pattern.fullmatch(f) for f in flags)
            assert len(set(flags)) == len(flags), "a flag is repeated"
        elif entry["kind"] == "portal_description":
            assert set(entry) == DESCRIPTION_ENTRY_KEYS, sorted(entry)
        else:
            raise AssertionError(f"unknown entry kind {entry['kind']!r}")
        keys_seen.append((entry["page_number"], entry["portal_block_id"]))
    assert len({identifier for _page, identifier in keys_seen}) == len(keys_seen)
    pages = [page for page, _identifier in keys_seen]
    assert pages == sorted(pages), "entries are not in page order"
