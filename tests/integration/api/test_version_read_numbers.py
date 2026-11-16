"""`UIP-S04-01`: ``getDocumentVersion`` carries the audit and the block count of the version it reads, without a database.

The tabs of a document's frame show «Разбор N», «Оптимизация N» and «Блоки N». The first two are the audit figures that
``listDocuments`` already attaches to each item; the third is the number of portal blocks of the version, once its block
index is built. The route is driven over a bare FastAPI application with fake ports, so what is asserted is the router's own
work: which port it asks, in which order, and what it puts on the wire. The shipped adapters' answers over a real run are
``test_version_read_numbers_db.py``'s.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from fastapi import APIRouter, FastAPI
from starlette.testclient import TestClient

from auditmanager.api.routers import (
    CorrelationMiddleware,
    FailureEnvelopeMiddleware,
    install_exception_handlers,
)
from auditmanager.api.routers.documents import build_document_routes
from auditmanager.api.schemas.documents import DocumentAuditView, DocumentVersionView
from auditmanager.shared.errors import DomainError, ErrorCode

VERSION = "ver_01ARZ3NDEKTSV4RRFFQ69G5FAV"
UNKNOWN = "ver_01ARZ3NDEKTSV4RRFFQ69G5FAW"
DOCUMENT = "doc_01ARZ3NDEKTSV4RRFFQ69G5FAV"
PROJECT = "prj_01ARZ3NDEKTSV4RRFFQ69G5FAV"
RUN = "run_01ARZ3NDEKTSV4RRFFQ69G5FAV"
CONTRACT = Path(__file__).resolve().parents[3] / "contracts" / "api" / "v1" / "openapi.json"

#: Four different numbers, so a figure read from the wrong field cannot pass.
AUDIT = DocumentAuditView(
    state="awaiting_decision", partial=False, result_run_id=RUN, finding_count=7, undecided_finding_count=3,
    optimisation_proposal_count=5, optimisation_undecided_count=2,
)


def _view(version_uid: str = VERSION) -> DocumentVersionView:
    return DocumentVersionView(
        version_uid=version_uid, document_uid=DOCUMENT, project_uid=PROJECT, version_ordinal=1, byte_size=10,
        sha256="a" * 64, page_count=1, published_at=datetime(2026, 11, 17, tzinfo=timezone.utc),
        display_title="СП-7-АР",
    )


class FakeDocuments:
    def __init__(self) -> None:
        self.asked: list[tuple[str, Any]] = []

    def get_version(self, *, version_uid: str) -> DocumentVersionView:
        self.asked.append(("get_version", version_uid))
        if version_uid != VERSION:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="DocumentVersion")
        return _view(version_uid)

    def document_audits(self, *, version_uids: Any) -> dict[str, DocumentAuditView]:
        self.asked.append(("document_audits", list(version_uids)))
        return {name: AUDIT for name in version_uids}

    def list_documents(self, **_: Any) -> tuple[DocumentVersionView, ...]:
        self.asked.append(("list_documents", None))
        return (_view(),)

    def list_versions(self, **_: Any) -> tuple[DocumentVersionView, ...]:
        return (_view(),)


class FakeBlocks:
    """``BlockPort.portal_block_count`` and nothing else: any other read is a failure of the router."""

    def __init__(self, count: int | None) -> None:
        self.count = count
        self.asked: list[str] = []

    def portal_block_count(self, *, version_uid: str) -> int | None:
        self.asked.append(version_uid)
        return self.count


def _client(documents: FakeDocuments, blocks: FakeBlocks | None) -> TestClient:
    router = APIRouter()
    build_document_routes(router, documents, blocks)  # type: ignore[arg-type]
    app = FastAPI()
    install_exception_handlers(app)
    app.include_router(router)
    app.add_middleware(FailureEnvelopeMiddleware)
    app.add_middleware(CorrelationMiddleware)
    return TestClient(app, raise_server_exceptions=False)


def test_the_read_carries_the_four_audit_figures_and_the_block_count() -> None:
    documents, blocks = FakeDocuments(), FakeBlocks(42)
    answer = _client(documents, blocks).get(f"/versions/{VERSION}")
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["block_count"] == 42
    audit = body["audit"]
    assert (
        audit["finding_count"], audit["undecided_finding_count"],
        audit["optimisation_proposal_count"], audit["optimisation_undecided_count"],
    ) == (7, 3, 5, 2)
    assert audit == {
        "state": "awaiting_decision", "partial": False, "result_run_id": RUN, "finding_count": 7,
        "undecided_finding_count": 3, "optimisation_proposal_count": 5, "optimisation_undecided_count": 2,
    }
    assert documents.asked == [("get_version", VERSION), ("document_audits", [VERSION])]
    assert blocks.asked == [VERSION]


def test_the_audit_is_the_one_the_listing_attaches_to_the_same_version() -> None:
    """The read and the listing take the figures from one port call, so they cannot be told apart."""
    client = _client(FakeDocuments(), FakeBlocks(42))
    listed = client.get(f"/projects/{PROJECT}/documents").json()["items"][0]
    read = client.get(f"/versions/{VERSION}").json()
    assert listed["version_uid"] == read["version_uid"] == VERSION
    assert listed["audit"] == read["audit"]


def test_no_index_means_no_property_and_never_zero() -> None:
    answer = _client(FakeDocuments(), FakeBlocks(None)).get(f"/versions/{VERSION}")
    assert answer.status_code == 200
    assert "block_count" not in answer.json(), "an index that is not built is absent, not a zero"
    assert "audit" in answer.json(), "the audit does not depend on the index"


def test_a_built_index_with_no_block_is_a_zero_and_is_sent() -> None:
    """Absent and zero are different facts on the wire: the second says an index exists and holds nothing."""
    body = _client(FakeDocuments(), FakeBlocks(0)).get(f"/versions/{VERSION}").json()
    assert body["block_count"] == 0


def test_an_application_without_a_block_port_serves_the_read_without_the_number() -> None:
    body = _client(FakeDocuments(), None).get(f"/versions/{VERSION}").json()
    assert "block_count" not in body and body["audit"]["finding_count"] == 7


def test_an_unknown_version_is_not_found_before_anything_else_is_read() -> None:
    documents, blocks = FakeDocuments(), FakeBlocks(42)
    answer = _client(documents, blocks).get(f"/versions/{UNKNOWN}")
    assert answer.status_code == 404 and answer.json()["error_code"] == "not_found"
    assert documents.asked == [("get_version", UNKNOWN)], "no audit is read for a version that does not exist"
    assert blocks.asked == []


def test_only_the_single_read_carries_the_block_count() -> None:
    """The listing and the version list read no index: the property is on ``getDocumentVersion`` and nowhere else."""
    client = _client(FakeDocuments(), FakeBlocks(42))
    assert "block_count" not in client.get(f"/projects/{PROJECT}/documents").json()["items"][0]
    assert "block_count" not in client.get(f"/documents/{DOCUMENT}/versions").json()["items"][0]


def test_the_contract_declares_the_new_property_optional_and_the_audit_it_reuses() -> None:
    """Additive and nothing else: an optional property, no new schema, the same ``DocumentAudit`` on the read."""
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    version = contract["components"]["schemas"]["DocumentVersion"]
    assert "block_count" not in version["required"], "a required property would break every existing reader"
    declared = version["properties"]["block_count"]
    assert (declared["type"], declared["minimum"]) == ("integer", 0)
    assert version["properties"]["audit"] == {"$ref": "#/components/schemas/DocumentAudit"}
    assert version["additionalProperties"] is False


@pytest.mark.parametrize("bad", [True, 1.5, "7", -1, None])
def test_a_stage_result_without_a_usable_number_is_no_number(bad: Any) -> None:
    """What the adapter accepts as a recorded count: a non-negative integer, never a flag, a float or a guess."""
    from auditmanager.bootstrap.adapters import BlockAdapter

    assert BlockAdapter._recorded_block_count({"portal_block_count": bad}) is None
    assert BlockAdapter._recorded_block_count({}) is None
    assert BlockAdapter._recorded_block_count({"portal_block_count": 0}) == 0
    assert BlockAdapter._recorded_block_count({"portal_block_count": 12}) == 12
