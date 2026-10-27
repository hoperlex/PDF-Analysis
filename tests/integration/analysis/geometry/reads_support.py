"""Helpers for the two ``BlockAdapter`` suites over a real run (`W55B-GEOMETRY-01`). Not a test module.

The run harness of ``tests/integration/runs`` is loaded **by path** (as ``tests/integration/exports``
and the recognised-text suite load it); each test module binds the harness fixtures it uses.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.bootstrap.adapters import BlockAdapter
from auditmanager.documents import DocumentRepository, ManifestEntry
from auditmanager.documents.public import (
    MANIFEST_ROLE_MARKDOWN,
    MANIFEST_ROLE_SOURCE_DOCUMENT,
    MANIFEST_ROLE_STRUCTURED_COMPANION,
)
from auditmanager.runs import RunRepository, execute_run, start_audit_run
from auditmanager.storage import sha256_of
from auditmanager.storage.blob_repository import BlobMetadataRepository
from auditmanager.storage.models import VerifiedBlob, parse_blob_role
from tests.integration.analysis.recognised.recognised_support import members
from tests.support.v1_reference_profile import V1_REFERENCE_PROFILE, resolve_reference_profile

_HARNESS_NAME = "b5_run_harness"
_HARNESS_PATH = Path(__file__).resolve().parents[2] / "runs" / "harness.py"
if _HARNESS_NAME in sys.modules:
    harness: ModuleType = sys.modules[_HARNESS_NAME]
else:
    _spec = importlib.util.spec_from_file_location(_HARNESS_NAME, _HARNESS_PATH)
    assert _spec is not None and _spec.loader is not None
    harness = importlib.util.module_from_spec(_spec)
    sys.modules[_HARNESS_NAME] = harness
    _spec.loader.exec_module(harness)

TEXT_ID = "blk_285e293c6614ba032cb547f00c83b5f6"
STAMP_ID = "blk_7109ac26cf708a9e7e83d003863990a7"
IMAGE_ID = "blk_91bef18c38cab738e6446aaa100fbd33"
POLYGON_ID = "blk_cf8cec69470764643bd45084fc86f83c"
ABSENT_VERSION = "ver_01ARZ3NDEKTSV4RRFFQ69G5FAV"


def publish(session: Session, store: Any, payload: bytes, *, role: str, media_type: str) -> Any:
    published = store.put_blob(
        payload, declared_sha256=sha256_of(payload), declared_size=len(payload),
        role=parse_blob_role(role), media_type=media_type,
    )
    blobs = BlobMetadataRepository()
    blobs.record_verified(
        session,
        VerifiedBlob(
            blob_id=published.blob_id, upload_token=f"geometry-{role}", sha256=published.sha256,
            size=published.size, role=published.role, media_type=published.media_type,
        ),
    )
    blobs.mark_available(session, published.blob_id)
    return published


def seed_bundle_version(session: Session, store: Any, *, markdown: bytes | None = None) -> str:
    """A version published from ``ar_baseline.zip``: the PDF, the block list, the markdown."""
    bundle = members("ar_baseline.zip")
    entries = []
    for manifest_role, blob_role, media_type, payload in (
        (MANIFEST_ROLE_SOURCE_DOCUMENT, "source_document", "application/pdf", bundle.pdf),
        (MANIFEST_ROLE_STRUCTURED_COMPANION, "source_structured_companion", "application/json", bundle.block_list),
        (MANIFEST_ROLE_MARKDOWN, "source_markdown", "text/markdown", markdown or bundle.markdown),
    ):
        published = publish(session, store, payload, role=blob_role, media_type=media_type)
        entries.append(
            ManifestEntry(role=manifest_role, blob_id=published.blob_id, sha256=published.sha256,
                          size_bytes=published.size, media_type=published.media_type)
        )
    documents = DocumentRepository()
    project = documents.create_project(session, "Проект с пакетом портала")
    document_uid = documents.create_document(
        session, project_uid=project.project_uid, display_title="СП-7-АР", section="AR"
    )
    return str(
        documents.publish_version(
            session, document_uid=document_uid, media_type="application/pdf",
            byte_size=len(bundle.pdf), sha256=sha256_of(bundle.pdf), page_count=8,
            source_filename="ar_baseline.pdf", entries=tuple(entries),
            text_character_count=3800, textless_pages=(), recognised_character_count=0,
        )
    )


def run_published(session: Session, version_uid: str, key: Any, store: Any, adapter: Any, config: Any) -> str:
    started = start_audit_run(
        session, version_uid=version_uid, analysis_profile_id=str(V1_REFERENCE_PROFILE.analysis_profile_id),
        prompt_bundle_id=str(V1_REFERENCE_PROFILE.prompt_bundle.prompt_bundle_id), provider_mode="recorded", idempotency_key=key,
    )
    result = execute_run(session, started.run_id, blob_store=store, adapter=adapter, provider_config=config, text_profiles=resolve_reference_profile)
    assert result.terminal_state == "published", dict(result.stage_statuses)
    return str(started.run_id)


def block_adapter(session: Session, store: Any) -> BlockAdapter:
    factory = sessionmaker(
        bind=session.connection(), expire_on_commit=False, future=True,
        join_transaction_mode="create_savepoint",
    )
    return BlockAdapter(factory, blob_store=store)


def stage_result(session: Session, run_id: str, stage_id: str) -> Any:
    return next(r for r in RunRepository().stage_results(session, run_id) if r.stage_id == stage_id)


def crop_blobs(session: Session, run_id: str) -> list[str]:
    """The ``geometry.crop_image`` blobs the run's geometry stage recorded, in its order."""
    return [a["blob_id"] for a in stage_result(session, run_id, "page_geometry_extraction").artifacts
            if a["role"] == "geometry.crop_image"]


@pytest.fixture
def produced(session, blob_store, recorded_adapter, provider_config, new_key) -> dict[str, Any]:
    version_uid = seed_bundle_version(session, blob_store)
    adapter = block_adapter(session, blob_store)
    before = adapter.list_portal_blocks(version_uid=version_uid)
    run_id = run_published(session, version_uid, new_key("geometry-produced"), blob_store, recorded_adapter, provider_config)
    return {"version_uid": version_uid, "run_id": run_id, "before": before, "adapter": adapter}
