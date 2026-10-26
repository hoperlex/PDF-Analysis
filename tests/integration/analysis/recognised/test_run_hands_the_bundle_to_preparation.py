"""The run executor hands a portal bundle's markdown and block list to ``source_preparation``.

`W55B-RECOGNISED-01`, on the lane's real PostgreSQL and S3. ``runs/executor.py`` used to seed
the stage with ``source.document`` alone, so a bundle's recognised text could never be
published by a real run. This drives ``start_audit_run`` and ``execute_run`` (the recorded
adapter, offline) over a version whose manifest holds the bundle's three members, and reads
the persisted ``stage_result`` back: ``prepared.recognised_text`` is among
``source_preparation``'s artifacts. A version without a bundle publishes none.

The run harness of ``tests/integration/runs`` is loaded **by path**, as
``tests/integration/exports`` loads it, and its fixtures are bound here.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from sqlalchemy.orm import Session

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

_no_network = harness._no_network
engine = harness.engine
blob_store = harness.blob_store
session = harness.session
provider_config = harness.provider_config
recorded_adapter = harness.recorded_adapter
seeded = harness.seeded
new_key = harness.new_key

RECOGNISED = "prepared.recognised_text"


def _publish(session: Session, store: Any, payload: bytes, *, role: str, media_type: str) -> Any:
    published = store.put_blob(
        payload,
        declared_sha256=sha256_of(payload),
        declared_size=len(payload),
        role=parse_blob_role(role),
        media_type=media_type,
    )
    blobs = BlobMetadataRepository()
    blobs.record_verified(
        session,
        VerifiedBlob(
            blob_id=published.blob_id,
            upload_token=f"recognised-{role}",
            sha256=published.sha256,
            size=published.size,
            role=published.role,
            media_type=published.media_type,
        ),
    )
    blobs.mark_available(session, published.blob_id)
    return published


def _seed_bundle_version(session: Session, store: Any) -> str:
    """A version published from ``ar_baseline.zip``: the PDF, the block list, the markdown."""
    bundle = members("ar_baseline.zip")
    entries = []
    for manifest_role, blob_role, media_type, payload in (
        (MANIFEST_ROLE_SOURCE_DOCUMENT, "source_document", "application/pdf", bundle.pdf),
        (MANIFEST_ROLE_STRUCTURED_COMPANION, "source_structured_companion", "application/json", bundle.block_list),
        (MANIFEST_ROLE_MARKDOWN, "source_markdown", "text/markdown", bundle.markdown),
    ):
        published = _publish(session, store, payload, role=blob_role, media_type=media_type)
        entries.append(
            ManifestEntry(
                role=manifest_role,
                blob_id=published.blob_id,
                sha256=published.sha256,
                size_bytes=published.size,
                media_type=published.media_type,
            )
        )
    documents = DocumentRepository()
    project = documents.create_project(session, "Проект с пакетом портала")
    document_uid = documents.create_document(
        session, project_uid=project.project_uid, display_title="СП-7-АР", section="AR"
    )
    version_uid = documents.publish_version(
        session,
        document_uid=document_uid,
        media_type="application/pdf",
        byte_size=len(bundle.pdf),
        sha256=sha256_of(bundle.pdf),
        page_count=8,
        source_filename="ar_baseline.pdf",
        entries=tuple(entries),
        text_character_count=3800,
        textless_pages=(),
        recognised_character_count=0,
    )
    return str(version_uid)


def _execute(session: Session, version_uid: str, key: Any, store: Any, adapter: Any, config: Any) -> Any:
    started = start_audit_run(
        session,
        version_uid=version_uid,
        analysis_profile_id=str(V1_REFERENCE_PROFILE.analysis_profile_id),
        prompt_bundle_id=str(V1_REFERENCE_PROFILE.prompt_bundle.prompt_bundle_id),
        provider_mode="recorded",
        idempotency_key=key,
    )
    result = execute_run(
        session, started.run_id, blob_store=store, adapter=adapter, provider_config=config,
        text_profiles=resolve_reference_profile,
    )
    rows = {row.stage_id: row for row in RunRepository().stage_results(session, started.run_id)}
    return result, rows


def test_a_run_over_a_bundle_version_publishes_the_recognised_text(
    session, blob_store, recorded_adapter, provider_config, new_key
) -> None:
    version_uid = _seed_bundle_version(session, blob_store)
    result, rows = _execute(
        session, version_uid, new_key("recognised-bundle"), blob_store, recorded_adapter, provider_config
    )

    preparation = rows["source_preparation"]
    assert preparation.status == "succeeded", preparation.error
    roles = {artifact["role"] for artifact in preparation.artifacts}
    assert roles == {"prepared.page_inventory", "prepared.text_layer", RECOGNISED}
    assert preparation.metrics["recognised_entry_count"] == 10

    reference = next(a for a in preparation.artifacts if a["role"] == RECOGNISED)
    from auditmanager.storage.public import parse_blob_id

    document = json.loads(blob_store.read(parse_blob_id(reference["blob_id"])))
    assert document["version_uid"] == version_uid
    assert len(document["entries"]) == 10
    # The rest of the chain is untouched by the bundle: the recorded reply still matches.
    assert result.terminal_state == "published", dict(result.stage_statuses)


def test_a_run_over_a_version_without_a_bundle_publishes_none(
    session, seeded, blob_store, recorded_adapter, provider_config, new_key
) -> None:
    _result, rows = _execute(
        session, seeded.version_uid, new_key("recognised-bare"), blob_store, recorded_adapter, provider_config
    )
    preparation = rows["source_preparation"]
    assert preparation.status == "succeeded"
    assert {artifact["role"] for artifact in preparation.artifacts} == {
        "prepared.page_inventory",
        "prepared.text_layer",
    }
    assert "recognised_entry_count" not in preparation.metrics
