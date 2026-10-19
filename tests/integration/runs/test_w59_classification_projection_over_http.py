"""`W59-SECTION-SEAL-01`: every read that returns ``DocumentVersion`` projects ``classification``.

``listDocuments`` (the current version of each document -- what the project screen groups
by), ``listVersions`` and ``getDocumentVersion``, through the shipped ``DocumentAdapter``
over the shipped ``IngestService`` and the real ASGI app, against the lane's own
PostgreSQL. A classified version carries the stored stage, section and first confirmer on
all three; an unclassified one carries no ``classification`` property at all (optional, not
null); a newer version of the same document starts without one, and ``listDocuments`` then
shows that newer, unclassified version while ``listVersions`` still shows the older one's.

**This module commits** and binds no ``_no_network`` guard, for the reasons
``test_w59_section_routing_over_http.py`` gives; nothing here runs or spends.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker
from starlette.testclient import TestClient

from auditmanager.access.accounts import AccountRepository as AccountAccessRepository
from auditmanager.access.repository import UserRepository as UserAccessRepository
from auditmanager.analysis.text.profile_registry import load_text_profile_registry
from auditmanager.api.app import create_asgi_app
from auditmanager.api.routers import build_router
from auditmanager.api.security import API_TOKEN_VARIABLE, build_signer
from auditmanager.bootstrap.adapters import CredentialAdapter, DocumentAdapter, SectionAdapter
from auditmanager.documents.public import DocumentRepository
from auditmanager.ingest import IngestService
from auditmanager.shared.identity import DocumentUid, VersionUid

SECRET = "w59-classification-projection-token"


@pytest.fixture(autouse=True)
def _no_network() -> None:
    """Replaces the run suite's guard for this module; see the module docstring."""


class _Carrier:
    """Nothing here starts a run; the app only needs something to shut down."""

    def submit(self, job: object) -> None:  # pragma: no cover - never called
        raise AssertionError("no run is started by this module")

    def shutdown(self) -> None:
        return None


class _Built:
    __slots__ = ("router", "carrier", "session_factory")

    def __init__(self, router: Any, sessions: Any) -> None:
        self.router = router
        self.carrier = _Carrier()
        self.session_factory = sessions


@pytest.fixture
def sessions(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


@pytest.fixture
def world(sessions: sessionmaker[Session], blob_store: Any, helpers: Any) -> Any:
    with sessions() as session:
        seeded = helpers.seed_version(session, blob_store)
        session.commit()
    return seeded


def _client(sessions: sessionmaker[Session], blob_store: Any) -> TestClient:
    signer = build_signer({API_TOKEN_VARIABLE: SECRET})
    assert signer is not None
    registry = load_text_profile_registry()
    router = build_router(
        projects=None,  # type: ignore[arg-type]
        documents=DocumentAdapter(IngestService(blob_store, session_factory=sessions)),
        runs=None,  # type: ignore[arg-type]
        findings=None,  # type: ignore[arg-type]
        decisions=None,  # type: ignore[arg-type]
        exports=None,  # type: ignore[arg-type]
        credentials=CredentialAdapter(
            sessions, users=UserAccessRepository(), accounts=AccountAccessRepository(), signer=signer
        ),
        sections=SectionAdapter(
            sessions, blob_store=blob_store, executable_sections=registry.executable_sections()
        ),
    )
    app = create_asgi_app(environ={API_TOKEN_VARIABLE: SECRET}, application=_Built(router, sessions))  # type: ignore[arg-type]
    return TestClient(app, raise_server_exceptions=False)


def _token() -> str:
    from am_test_accounts import provisioned_credential

    return provisioned_credential(SECRET, "w59-projection-expert")


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _version_reads(client: TestClient, token: str, seeded: Any, version_uid: str) -> dict[str, Any]:
    listed = client.get(f"/projects/{seeded.project_uid}/documents", headers=_headers(token))
    versions = client.get(f"/documents/{seeded.document_uid}/versions", headers=_headers(token))
    single = client.get(f"/versions/{version_uid}", headers=_headers(token))
    for answer in (listed, versions, single):
        assert answer.status_code == 200, answer.content
    return {
        "listDocuments": {item["version_uid"]: item for item in listed.json()["items"]},
        "listVersions": {item["version_uid"]: item for item in versions.json()["items"]},
        "getDocumentVersion": {single.json()["version_uid"]: single.json()},
    }


def test_all_three_reads_project_the_classification_and_an_unclassified_version_omits_it(
    sessions, blob_store, world
) -> None:
    client = _client(sessions, blob_store)
    token = _token()
    before = _version_reads(client, token, world, world.version_uid)
    for operation, items in before.items():
        assert "classification" not in items[world.version_uid], operation
        assert items[world.version_uid]["section"] == "AR", "the legacy section is not a classification"

    stored = client.put(
        f"/projects/{world.project_uid}/documents/{world.document_uid}/versions/"
        f"{world.version_uid}/classification",
        headers=_headers(token),
        content=json.dumps({"project_stage": "R", "section_code": "KJ"}).encode(),
    )
    assert stored.status_code == 200, stored.content

    after = _version_reads(client, token, world, world.version_uid)
    for operation, items in after.items():
        assert items[world.version_uid]["classification"] == stored.json(), operation


def test_a_newer_version_is_listed_unclassified_and_the_older_keeps_its_classification(
    sessions, blob_store, world
) -> None:
    client = _client(sessions, blob_store)
    token = _token()
    stored = client.put(
        f"/projects/{world.project_uid}/documents/{world.document_uid}/versions/"
        f"{world.version_uid}/classification",
        headers=_headers(token),
        content=json.dumps({"project_stage": "P", "section_code": "AR"}).encode(),
    ).json()
    with sessions() as session:
        documents = DocumentRepository()
        base = documents.get_version(session, VersionUid.parse(world.version_uid))
        newer = str(
            documents.publish_version(
                session, document_uid=DocumentUid.parse(world.document_uid),
                media_type=base.media_type, byte_size=base.byte_size, sha256=base.sha256,
                page_count=base.page_count, source_filename=None, entries=base.manifest,
            )
        )
        session.commit()
    reads = _version_reads(client, token, world, newer)
    assert list(reads["listDocuments"]) == [newer]
    assert "classification" not in reads["listDocuments"][newer]
    assert "classification" not in reads["getDocumentVersion"][newer]
    assert "classification" not in reads["listVersions"][newer]
    assert reads["listVersions"][world.version_uid]["classification"] == stored
