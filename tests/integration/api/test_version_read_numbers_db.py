"""`UIP-S04-01`: the numbers ``getDocumentVersion`` carries, over a real run, on the lane's PostgreSQL and S3.

``test_version_read_numbers.py`` shows what the route does with the answers of its ports; this shows the shipped adapters'
answers. ``start_audit_run`` and ``execute_run`` (the recorded adapter, offline) carry a portal-bundle version through the real
chain, and the route is then asked for the version through the shipped ``DocumentAdapter`` and ``BlockAdapter``:

* before any run the version has no block index: the read carries no ``block_count`` (not a zero) and an audit of ``not_run``;
* after the run ``block_count`` is the number of blocks ``listVersionPortalBlocks`` lists for that version, and the audit is
  the one ``listDocuments`` attaches to the same version;
* a version without a portal bundle (the shape of a document admitted for comparison only) ran its geometry stage and has a
  text-line index, yet carries no ``block_count``: the number is the portal blocks', not the text lines';
* a stage result that recorded no usable number gives no number, never a zero and never a read of the artifact;
* the number is read without opening any object: the blob store is asked for nothing.

The run harness of ``tests/integration/runs`` is loaded by path (``reads_support``).
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import APIRouter, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from starlette.testclient import TestClient

from auditmanager.api.routers import (
    CorrelationMiddleware,
    FailureEnvelopeMiddleware,
    install_exception_handlers,
)
from auditmanager.api.routers.documents import build_document_routes
from auditmanager.bootstrap.adapters import BlockAdapter, DocumentAdapter
from auditmanager.ingest import IngestService
from auditmanager.shared.errors import DomainError, ErrorCode
from tests.integration.analysis.geometry.reads_support import (
    ABSENT_VERSION,
    harness,
    produced,
)
from tests.integration.analysis.geometry.reads_support import run_published as _run
from tests.integration.analysis.geometry.reads_support import stage_result as _stage

engine = harness.engine
blob_store = harness.blob_store
session = harness.session
provider_config = harness.provider_config
recorded_adapter = harness.recorded_adapter
seeded = harness.seeded
new_key = harness.new_key

__all__ = ["produced"]


@pytest.fixture(autouse=True)
def _no_network() -> None:
    """Replaces the run suite's socket guard for this module.

    The guard refuses every new socket, and the ASGI test client needs one for its event loop. Nothing here can call a
    provider: the runs are the recorded adapter's (``recorded_adapter``, no key) and the reads are the database's."""


def _factory(session: Any) -> sessionmaker:
    return sessionmaker(
        bind=session.connection(), expire_on_commit=False, future=True, join_transaction_mode="create_savepoint"
    )


def _client(session: Any, blob_store: Any) -> tuple[TestClient, BlockAdapter]:
    factory = _factory(session)
    blocks = BlockAdapter(factory, blob_store=blob_store)
    router = APIRouter()
    build_document_routes(router, DocumentAdapter(IngestService(blob_store, session_factory=factory), factory), blocks)
    app = FastAPI()
    install_exception_handlers(app)
    app.include_router(router)
    app.add_middleware(FailureEnvelopeMiddleware)
    app.add_middleware(CorrelationMiddleware)
    return TestClient(app, raise_server_exceptions=False), blocks


def _read(client: TestClient, version_uid: str) -> dict[str, Any]:
    answer = client.get(f"/versions/{version_uid}")
    assert answer.status_code == 200, answer.text
    return answer.json()


def test_no_index_before_a_run_and_the_portal_blocks_count_after_it(session, blob_store, produced) -> None:
    client, blocks = _client(session, blob_store)
    version_uid = produced["version_uid"]
    assert produced["before"].status == "not_produced"

    after = _read(client, version_uid)
    listed = blocks.list_portal_blocks(version_uid=version_uid)
    assert listed.status == "produced" and len(listed.blocks) == 12
    assert after["block_count"] == len(listed.blocks) == 12
    assert after["audit"]["result_run_id"] == produced["run_id"], "the run published, so it is the version's result run"

    # The same version, before its run: put the clock back by asking a version no run has reached.
    other = harness.seed_version(session, blob_store)
    never_run = _read(client, other.version_uid)
    assert "block_count" not in never_run, "no index is no property, not a zero"
    assert never_run["audit"] == {
        "state": "not_run", "partial": False, "finding_count": 0, "undecided_finding_count": 0,
    }


def test_the_audit_of_the_read_is_the_one_the_listing_attaches(session, blob_store, produced) -> None:
    client, _ = _client(session, blob_store)
    version_uid = produced["version_uid"]
    read = _read(client, version_uid)
    project_uid = read["project_uid"]
    listing = client.get(f"/projects/{project_uid}/documents")
    assert listing.status_code == 200, listing.text
    listed = {item["version_uid"]: item for item in listing.json()["items"]}[version_uid]
    assert read["audit"] == listed["audit"]
    assert read["audit"]["finding_count"] > 0, "the recorded run published findings, so the figure is not vacuous"
    assert "block_count" not in listed, "only the single read carries the block count"


def test_a_version_without_a_bundle_has_a_text_line_index_and_no_block_count(
    session, seeded, blob_store, recorded_adapter, provider_config, new_key
) -> None:
    run_id = _run(session, seeded.version_uid, new_key("read-numbers-bare"), blob_store, recorded_adapter, provider_config)
    assert _stage(session, run_id, "page_geometry_extraction").metrics["block_count"] > 0
    client, blocks = _client(session, blob_store)
    assert blocks.get_block_index(version_uid=seeded.version_uid).status == "produced"
    body = _read(client, seeded.version_uid)
    assert "block_count" not in body, "the text lines are not the portal's blocks"
    assert body["audit"]["result_run_id"] == run_id


def test_a_stage_result_that_recorded_no_number_gives_no_number(session, blob_store, produced) -> None:
    """The metric is removed from the stage result: absent, not zero, and the listing of blocks is untouched."""
    client, blocks = _client(session, blob_store)
    version_uid = produced["version_uid"]
    assert _read(client, version_uid)["block_count"] == 12
    changed = session.execute(
        text(
            "UPDATE stage_result SET metrics = metrics - 'portal_block_count' "
            "WHERE run_id = :run AND stage_id = 'page_geometry_extraction'"
        ),
        {"run": produced["run_id"]},
    ).rowcount
    assert changed == 1
    assert "block_count" not in _read(client, version_uid)
    assert len(blocks.list_portal_blocks(version_uid=version_uid).blocks) == 12


def test_the_count_opens_no_object(session, blob_store, produced) -> None:
    """The number comes from the stage result: the store is not asked for a byte, and no file is parsed."""
    _, blocks = _client(session, blob_store)

    class Untouchable:
        def __getattr__(self, name: str) -> Any:  # pragma: no cover - reaching it is the failure
            raise AssertionError(f"the block count read the blob store ({name})")

    asked = BlockAdapter(_factory(session), blob_store=Untouchable())
    assert asked.portal_block_count(version_uid=produced["version_uid"]) == 12
    assert blocks.portal_block_count(version_uid=produced["version_uid"]) == 12


def test_an_unknown_version_is_not_found(session, blob_store, produced) -> None:
    client, blocks = _client(session, blob_store)
    with pytest.raises(DomainError) as raised:
        blocks.portal_block_count(version_uid=ABSENT_VERSION)
    assert raised.value.code == ErrorCode.NOT_FOUND
    answer = client.get(f"/versions/{ABSENT_VERSION}")
    assert answer.status_code == 404 and answer.json()["error_code"] == "not_found"
