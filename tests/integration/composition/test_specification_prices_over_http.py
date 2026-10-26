"""`W60-OPT-MATCH-01`, end to end: «Спецификация и цены» over HTTP.

The composed ASGI application (``create_asgi_app``) with the recorded provider, against the
lane's own PostgreSQL and MinIO, driven with a real expert credential. One portal bundle is
uploaded; then, in the order the read checks them, every state appears as its input does:
``version_unclassified``, ``price_list_missing`` once the version is classified ``AR``,
``analysis_missing`` once the project has a price list (uploaded through the optimisation
boundary, as the price-list operation will), and ``ready`` once a recorded run has
published. The saved text layer is read from MinIO by the shipped adapter, held to the
digest its stage row recorded. The baseline document has no specification table, so the
ready answer is the honest empty one: no table, no row, no total, nothing excluded.

A second set classified ``KJ`` is ``section_not_ar``; a set of another project is ``404``;
malformed paging is ``422``. The matching itself is proved in
``tests/integration/optimisation/test_project_match.py`` and the unit suites.
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

import pytest
from starlette.testclient import TestClient

from auditmanager.api.routers.idempotency import IDEMPOTENCY_HEADER
from auditmanager.api.security import API_TOKEN_VARIABLE
from tests.support.published_run import publish_reference_run

DEPLOYMENT_SECRET = "w60-opt-match-over-http-token"
ACCOUNT = "w60-opt-match"
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
BASELINE_BUNDLE = REPOSITORY_ROOT / "fixtures" / "synthetic" / "ar" / "bundles" / "ar_baseline.zip"
PRICE_LIST = "Наименование;Ед. изм.;Цена;Валюта\nМеталлический щит МЩ-1;шт;15000;RUB\n".encode()


def _token() -> str:
    from am_test_accounts import provisioned_credential

    return provisioned_credential(DEPLOYMENT_SECRET, ACCOUNT)


def _upload(client: TestClient, auth: dict[str, str], project_uid: str, tag: str) -> dict[str, Any]:
    boundary = "w60specificationboundary"
    head = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
        f'filename="ar_baseline.zip"\r\nContent-Type: application/zip\r\n\r\n'
    ).encode("utf-8")
    tail = f"\r\n--{boundary}--\r\n".encode("utf-8")
    answer = client.post(
        f"/projects/{project_uid}/documents",
        headers=auth | {
            IDEMPOTENCY_HEADER: f"w60spec-{tag}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        content=head + BASELINE_BUNDLE.read_bytes() + tail,
    )
    assert answer.status_code == 201, answer.content
    return answer.json()


def _project(client: TestClient, auth: dict[str, str], tag: str) -> str:
    answer = client.post(
        "/projects",
        headers=auth | {IDEMPOTENCY_HEADER: f"w60spec-{tag}", "Content-Type": "application/json"},
        content=json.dumps({"name": f"W60 specification {tag}"}).encode("utf-8"),
    )
    assert answer.status_code == 201, answer.content
    return answer.json()["project_uid"]


def _upload_price_list(project_uid: str, tag: str) -> str:
    """The project's price list through the optimisation boundary, on the lane's services."""
    from am_test_accounts import provisioned_record

    from auditmanager.optimisation.public import PriceListUploads
    from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
    from auditmanager.shared.db.engine import create_database_engine
    from auditmanager.shared.db.session import create_session_factory
    from auditmanager.storage import S3BlobStore, S3StorageSettings

    engine = create_database_engine(
        DatabaseSettings(url=parse_database_url(os.environ["DATABASE_URL"]))
    )
    try:
        uploaded = PriceListUploads(
            S3BlobStore(S3StorageSettings.from_env()),
            session_factory=create_session_factory(engine),
        ).upload(
            project_uid=project_uid,
            content=PRICE_LIST,
            source_filename="Прайс.csv",
            idempotency_key=f"w60spec-{tag}-prices",
            actor_uid=str(provisioned_record(ACCOUNT).user_uid),
        )
        return uploaded.revision.price_list_id
    finally:
        engine.dispose()


@pytest.fixture(scope="module")
def world() -> dict[str, Any]:
    assert os.environ.get("DATABASE_URL"), "this suite needs the lane's .env loaded"
    for leaked in ("ANTHROPIC_API_KEY", "PROXY_LLM_BASE_URL", "PROXY_LLM_TOKEN"):
        assert leaked not in os.environ, f"{leaked} reached this suite"
    from auditmanager.api.app import create_asgi_app

    app = create_asgi_app(environ=dict(os.environ) | {
        "AUDITMANAGER_PROVIDER_MODE": "recorded",
        API_TOKEN_VARIABLE: DEPLOYMENT_SECRET,
    })
    client = TestClient(app, raise_server_exceptions=False)
    auth = {"Authorization": f"Bearer {_token()}"}
    tag = uuid.uuid4().hex[:12]
    project_uid = _project(client, auth, f"{tag}-prj")
    other_project_uid = _project(client, auth, f"{tag}-other-prj")
    ar = _upload(client, auth, project_uid, f"{tag}-ar")
    kj = _upload(client, auth, project_uid, f"{tag}-kj")
    foreign = _upload(client, auth, other_project_uid, f"{tag}-foreign")
    return {
        "app": app, "client": client, "auth": auth, "tag": tag, "project_uid": project_uid,
        "ar": ar, "kj": kj, "foreign": foreign,
    }


def _read(world: dict[str, Any], document_uid: str, **query: Any) -> Any:
    return world["client"].get(
        f"/projects/{world['project_uid']}/documents/{document_uid}/specification-prices",
        params=query, headers=world["auth"],
    )


def _classify(world: dict[str, Any], uploaded: dict[str, Any], section: str) -> None:
    answer = world["client"].put(
        f"/projects/{world['project_uid']}/documents/{uploaded['document_uid']}"
        f"/versions/{uploaded['version_uid']}/classification",
        headers=world["auth"] | {"Content-Type": "application/json"},
        content=json.dumps({"project_stage": "R", "section_code": section}).encode("utf-8"),
    )
    assert answer.status_code == 200, answer.content


def test_every_state_appears_as_its_input_does(world) -> None:
    ar = world["ar"]
    first = _read(world, ar["document_uid"])
    assert first.status_code == 200, first.content
    body = first.json()
    assert body["state"] == "version_unclassified"
    assert (body["version_uid"], body["section_code"], body["price_list"]) == (
        ar["version_uid"], None, None,
    )
    assert (body["extraction"], body["matching"], body["rows"]) == (None, None, None)

    _classify(world, ar, "AR")
    no_prices = _read(world, ar["document_uid"]).json()
    assert (no_prices["state"], no_prices["project_stage"], no_prices["section_code"]) == (
        "price_list_missing", "R", "AR",
    )

    price_list_id = _upload_price_list(world["project_uid"], world["tag"])
    unanalysed = _read(world, ar["document_uid"]).json()
    assert unanalysed["state"] == "analysis_missing"
    assert unanalysed["price_list"]["price_list_id"] == price_list_id
    assert (unanalysed["price_list"]["revision_number"], unanalysed["price_list"]["position_count"]) == (1, 1)
    assert unanalysed["price_list"]["source_filename"] == "Прайс.csv"
    assert unanalysed["run_id"] is None

    # `PROD-11-AR-V1-V2-REMOVAL-01`: the served startRun refuses an АР version, so the published run the АР reads need is made in-process (tests/support/published_run.py).
    refused = world["client"].post(
        "/runs",
        headers=world["auth"] | {
            IDEMPOTENCY_HEADER: f"w60spec-{world['tag']}-run",
            "Content-Type": "application/json",
        },
        content=json.dumps({"version_uid": ar["version_uid"]}).encode("utf-8"),
    )
    assert refused.status_code == 422, refused.content
    assert refused.json()["error_code"] == "section_profile_unavailable"
    run_id = publish_reference_run(ar["version_uid"], tag="spec-prices")
    state = world["client"].get(f"/runs/{run_id}", headers=world["auth"]).json()["state"]
    assert state == "published", state

    ready = _read(world, ar["document_uid"])
    assert ready.status_code == 200, ready.content
    body = ready.json()
    assert body["state"] == "ready"
    assert body["run_id"] == run_id
    assert len(body["text_layer_sha256"]) == 64
    extraction = body["extraction"]
    assert extraction["algorithm"] == "specification-text-v1"
    assert (extraction["table_count"], extraction["row_count"], extraction["skipped_count"]) == (0, 0, 0)
    assert set(extraction["skipped_by_reason"].values()) == {0}
    assert body["matching"] == {
        "algorithm": "price-match-v1",
        "counts": {"matched": 0, "ambiguous": 0, "unmatched": 0},
        "totals": [],
        "excluded": {
            "no_position": 0, "unit_mismatch": 0, "row_unit_missing": 0, "ambiguous": 0,
            "quantity_not_numeric": 0,
        },
    }
    assert body["rows"] == {"offset": 0, "limit": 50, "total": 0, "next_offset": None, "items": []}


def test_a_set_of_another_section_is_not_priced(world) -> None:
    _classify(world, world["kj"], "KJ")
    body = _read(world, world["kj"]["document_uid"]).json()
    assert (body["state"], body["section_code"], body["rows"]) == ("section_not_ar", "KJ", None)


def test_a_set_of_another_project_is_404(world) -> None:
    answer = _read(world, world["foreign"]["document_uid"])
    assert answer.status_code == 404, answer.content
    assert answer.json()["error_code"] == "not_found"


@pytest.mark.parametrize("query", [{"limit": 0}, {"limit": 201}, {"offset": -1}])
def test_malformed_paging_is_422(world, query) -> None:
    answer = _read(world, world["ar"]["document_uid"], **query)
    assert answer.status_code == 422, answer.content
    assert answer.json()["error_code"] == "validation_failed"
