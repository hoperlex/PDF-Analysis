"""`W63-SECTION-FORM7-01`, end to end: «Оптимизация разделов» over HTTP.

The composed ASGI application (``create_asgi_app``) with the recorded provider, against the
lane's own PostgreSQL and MinIO, driven with a real expert credential. Four projects, each
with one portal bundle: two classified ``AR`` (one with a price list, one without), one
``KJ``, one left unclassified. In the order the read checks them:

* a section's membership is the *current* versions confirmed in it -- the KJ project never
  appears under AR, the unclassified one is listed as excluded;
* each project's price state is its own: ``priced`` (and a ``matching`` that is this project's
  only) or ``price_list_missing`` (no ``matching``, no figure);
* a member set is ``analysis_missing`` until a recorded run publishes, then ``ready`` with
  the extraction facts read from the saved text layer in MinIO (the baseline document has no
  specification table, so the honest empty answer: no table, no row, no total);
* the project filter, an unknown project (``404``), a section code outside the fifteen
  (``404``, the operation's own aggregate), malformed filters and paging (``422``).

The lane's database is long-lived and shared, so the section-wide read is asserted on
*membership of this suite's own projects* (and tolerates a ``section_too_large`` answer when
earlier runs left many ``AR`` sets behind); everything else is asserted through the project
filter. The rows, the pricing and the per-project totals are proved against PostgreSQL and
MinIO in ``tests/integration/optimisation/test_section_specification.py``.
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

DEPLOYMENT_SECRET = "w63-section-form7-over-http-token"
ACCOUNT = "w63-section-form7"
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
BASELINE_BUNDLE = REPOSITORY_ROOT / "fixtures" / "synthetic" / "ar" / "bundles" / "ar_baseline.zip"
PRICE_LIST = "Наименование;Ед. изм.;Цена;Валюта\nМеталлический щит МЩ-1;шт;15000;RUB\n".encode()


def _token() -> str:
    from am_test_accounts import provisioned_credential

    return provisioned_credential(DEPLOYMENT_SECRET, ACCOUNT)


def _project(client: TestClient, auth: dict[str, str], name: str, key: str) -> str:
    answer = client.post(
        "/projects",
        headers=auth | {IDEMPOTENCY_HEADER: f"w63sec-{key}", "Content-Type": "application/json"},
        content=json.dumps({"name": name}).encode("utf-8"),
    )
    assert answer.status_code == 201, answer.content
    return answer.json()["project_uid"]


def _upload(client: TestClient, auth: dict[str, str], project_uid: str, key: str) -> dict[str, Any]:
    boundary = "w63sectionboundary"
    head = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
        f'filename="ar_baseline.zip"\r\nContent-Type: application/zip\r\n\r\n'
    ).encode("utf-8")
    tail = f"\r\n--{boundary}--\r\n".encode("utf-8")
    answer = client.post(
        f"/projects/{project_uid}/documents",
        headers=auth | {
            IDEMPOTENCY_HEADER: f"w63sec-{key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        content=head + BASELINE_BUNDLE.read_bytes() + tail,
    )
    assert answer.status_code == 201, answer.content
    return answer.json()


def _classify(
    client: TestClient, auth: dict[str, str], project_uid: str, uploaded: dict[str, Any], section: str
) -> None:
    answer = client.put(
        f"/projects/{project_uid}/documents/{uploaded['document_uid']}"
        f"/versions/{uploaded['version_uid']}/classification",
        headers=auth | {"Content-Type": "application/json"},
        content=json.dumps({"project_stage": "R", "section_code": section}).encode("utf-8"),
    )
    assert answer.status_code == 200, answer.content


def _upload_price_list(project_uid: str, key: str) -> str:
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
            idempotency_key=f"w63sec-{key}-prices",
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
    projects = {
        name: _project(client, auth, f"W63 {name} {tag}", f"{tag}-{name}")
        for name in ("priced", "bare", "other", "loose")
    }
    uploads = {name: _upload(client, auth, uid, f"{tag}-{name}") for name, uid in projects.items()}
    for name, section in (("priced", "AR"), ("bare", "AR"), ("other", "KJ")):
        _classify(client, auth, projects[name], uploads[name], section)
    price_list_id = _upload_price_list(projects["priced"], tag)
    return {
        "app": app, "client": client, "auth": auth, "tag": tag, "projects": projects,
        "uploads": uploads, "price_list_id": price_list_id,
    }


def _read(world: dict[str, Any], section: str = "AR", **query: Any) -> Any:
    return world["client"].get(
        f"/sections/{section}/specification", params=query, headers=world["auth"]
    )


def _mine(world: dict[str, Any], body: dict[str, Any]) -> dict[str, dict[str, Any]]:
    by_uid = {project["project_uid"]: project for project in body["projects"]}
    return {name: by_uid[uid] for name, uid in world["projects"].items() if uid in by_uid}


def test_membership_is_the_current_versions_confirmed_in_the_section(world) -> None:
    projects, uploads = world["projects"], world["uploads"]
    answer = _read(world)
    assert answer.status_code == 200, answer.content
    body = answer.json()
    assert body["section_code"] == "AR"
    assert body["extraction_algorithm"] == "specification-text-v1"
    assert body["match_algorithm"] == "price-match-v1"
    if body["limit_reason"] == "projects":  # more projects than the scan bound: nothing listed
        assert body["state"] == "section_too_large" and body["projects"] == []
    else:
        assert body["state"] in ("ready", "section_too_large")
        mine = _mine(world, body)
        assert set(mine) == {"priced", "bare"}, "the KJ and the unclassified project are not members"
        assert {item["project_uid"] for item in body["projects"]} >= {
            projects["priced"], projects["bare"],
        }
        assert projects["other"] not in {item["project_uid"] for item in body["projects"]}
        excluded = {item["project_uid"]: item for item in body["excluded"]}
        if body["excluded_count"] <= len(body["excluded"]):
            assert excluded[projects["loose"]]["version_uid"] == uploads["loose"]["version_uid"]
            assert excluded[projects["loose"]]["reason"] == "version_unclassified"
            assert projects["other"] not in excluded and projects["priced"] not in excluded

    kj = _read(world, "KJ", project_uid=projects["other"]).json()
    assert kj["state"] == "ready"
    assert [item["project_uid"] for item in kj["projects"]] == [projects["other"]]
    assert kj["projects"][0]["sources"][0]["version_uid"] == uploads["other"]["version_uid"]
    assert kj["projects"][0]["sources"][0]["project_stage"] == "R"
    not_kj = _read(world, "KJ", project_uid=projects["priced"]).json()
    assert (not_kj["projects"], not_kj["rows"]["items"], not_kj["excluded"]) == ([], [], [])


def test_each_projects_price_state_and_sources_are_its_own(world) -> None:
    projects, uploads = world["projects"], world["uploads"]
    priced = _read(world, project_uid=projects["priced"]).json()
    assert priced["state"] == "ready" and priced["project_filter"] == projects["priced"]
    (project,) = priced["projects"]
    assert (project["price_state"], project["name"]) == ("priced", project["name"])
    assert project["price_list"]["price_list_id"] == world["price_list_id"]
    assert (project["price_list"]["revision_number"], project["price_list"]["position_count"]) == (1, 1)
    assert project["matching"]["algorithm"] == "price-match-v1"
    assert project["matching"]["totals"] == []
    (source,) = project["sources"]
    assert source["document_uid"] == uploads["priced"]["document_uid"]
    assert source["version_uid"] == uploads["priced"]["version_uid"]
    assert (source["state"], source["run_id"], source["row_count"], source["skipped_by_reason"]) == (
        "analysis_missing", None, None, None,
    )

    bare = _read(world, project_uid=projects["bare"]).json()
    (project,) = bare["projects"]
    assert (project["price_state"], project["price_list"], project["matching"]) == (
        "price_list_missing", None, None,
    )
    assert project["sources"][0]["state"] == "analysis_missing"
    assert (bare["source_count"], bare["row_count"]) == (1, 0)
    assert bare["rows"] == {"offset": 0, "limit": 50, "total": 0, "next_offset": None, "items": []}


def test_a_published_run_makes_its_set_ready_with_the_saved_text_read(world) -> None:
    projects, uploads, auth = world["projects"], world["uploads"], world["auth"]
    # `PROD-11-AR-V1-V2-REMOVAL-01`: the served startRun refuses an АР version, so the published run the АР reads need is made in-process (tests/support/published_run.py).
    refused = world["client"].post(
        "/runs",
        headers=auth | {
            IDEMPOTENCY_HEADER: f"w63sec-{world['tag']}-run",
            "Content-Type": "application/json",
        },
        content=json.dumps({"version_uid": uploads["priced"]["version_uid"]}).encode("utf-8"),
    )
    assert refused.status_code == 422, refused.content
    assert refused.json()["error_code"] == "section_profile_unavailable"
    run_id = publish_reference_run(uploads["priced"]["version_uid"], tag="sec-spec")
    state = world["client"].get(f"/runs/{run_id}", headers=auth).json()["state"]
    assert state == "published", state

    body = _read(world, project_uid=projects["priced"]).json()
    (project,) = body["projects"]
    (source,) = project["sources"]
    assert (source["state"], source["run_id"]) == ("ready", run_id)
    assert len(source["text_layer_sha256"]) == 64
    assert (source["table_count"], source["row_count"]) == (0, 0)
    assert set(source["skipped_by_reason"].values()) == {0}
    assert project["row_count"] == 0
    assert project["matching"] == {
        "algorithm": "price-match-v1",
        "counts": {"matched": 0, "ambiguous": 0, "unmatched": 0},
        "totals": [],
        "excluded": {
            "no_position": 0, "unit_mismatch": 0, "row_unit_missing": 0, "ambiguous": 0,
            "quantity_not_numeric": 0,
        },
    }
    # The other project's set is still unanalysed: a run is per version, never per section.
    other = _read(world, project_uid=projects["bare"]).json()
    assert other["projects"][0]["sources"][0]["state"] == "analysis_missing"


def test_a_text_search_narrows_rows_and_never_the_answer_around_them(world) -> None:
    projects = world["projects"]
    plain = _read(world, project_uid=projects["priced"]).json()
    searched = _read(world, project_uid=projects["priced"], q="щит").json()
    assert searched["query"] == "щит"
    assert searched["projects"] == plain["projects"]
    assert (searched["row_count"], searched["rows"]["total"], searched["rows"]["items"]) == (0, 0, [])


def test_unknown_project_and_unknown_section_are_404(world) -> None:
    unknown = _read(world, project_uid="prj_01M2545JSD15ETSNNV904X991F")
    assert unknown.status_code == 404, unknown.content
    assert unknown.json()["error_code"] == "not_found"
    assert unknown.json()["details"] == {"aggregate_type": "Project"}
    for code in ("XX", "ar", "АР"):
        answer = _read(world, code)
        assert answer.status_code == 404, (code, answer.content)
        assert answer.json()["details"] == {"aggregate_type": "SectionSpecification"}


@pytest.mark.parametrize(
    "query",
    [
        {"limit": 0}, {"limit": 201}, {"offset": -1}, {"project_uid": "prj_bad"}, {"q": "д" * 201},
    ],
)
def test_malformed_filters_and_paging_are_422(world, query) -> None:
    answer = _read(world, **query)
    assert answer.status_code == 422, answer.content
    assert answer.json()["error_code"] == "validation_failed"


def test_it_needs_a_credential(world) -> None:
    answer = world["client"].get("/sections/AR/specification")
    assert answer.status_code == 401, answer.content
