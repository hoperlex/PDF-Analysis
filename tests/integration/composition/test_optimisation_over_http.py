"""`W60-PRICE-LIST-01`, end to end: the six optimisation operations over the composed application.

The shipped ``create_asgi_app`` (recorded provider) against the lane's own PostgreSQL and MinIO,
driven with real credentials -- an expert, and an administrator made for this suite. What is
held:

* an expert uploads a CSV price list as multipart under an ``Idempotency-Key``: ``201`` with the
  revision, the exact repeat answers the same revision, another file under the same key is
  ``409``; an Excel 97 workbook is ``422`` with ``field: content``, ``constraint:
  price_list_format``; an administrator alone is ``403``;
* the revision list and the positions page answer the stored revision, its parse report (the
  stored maps as the contract's ordered lists) and each unit price as exact decimal text;
* the effective vendor lists answer all fifteen sections; the expert's project override and the
  administrator's global list are versioned, a stale ``expected_vendor_list_id`` is ``409`` with
  ``conflict_reason: vendor_list_changed``, and the global list is the administrator's alone;
* an unknown project and an unknown price list are ``404``;
* every object carries exactly its frozen schema's properties.

The lane database persists between runs, so every run works in a project of its own and keys
of its own.
"""

from __future__ import annotations

import json
import os
import secrets
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from auditmanager.api.security import API_TOKEN_VARIABLE

DEPLOYMENT_SECRET = "w60-price-list-over-http-token"
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CONTRACT = REPOSITORY_ROOT / "contracts" / "api" / "v1" / "openapi.json"
UNKNOWN_PROJECT = "prj_01M2545JSD15ETSNNV904X991F"
UNKNOWN_PRICE_LIST = "prl_01M2545JSD15ETSNNV904X991N"

PRICE_LIST = (
    "Код;Наименование;Ед. изм.;Цена, руб.;Поставщик;Раздел\n"
    "К-1;Кабель ВВГнг-LS 3х2,5;м;125,50;Кабельный завод;ЭОМ\n"
    "К-2;Труба ПП 20;м;по запросу;;ВК\n"
    "К-3;Щит ЩР-1;шт;12 345,67;;\n"
).encode("cp1251")


def _schema(name: str) -> dict[str, Any]:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))["components"]["schemas"][name]


def _exact_keys(body: dict[str, Any], schema: str) -> None:
    assert set(body) == set(_schema(schema)["properties"]), schema


@pytest.fixture(scope="module")
def client() -> TestClient:
    assert os.environ.get("DATABASE_URL"), "this suite needs the lane's .env loaded"
    for leaked in ("ANTHROPIC_API_KEY", "PROXY_LLM_BASE_URL", "PROXY_LLM_TOKEN"):
        assert leaked not in os.environ, f"{leaked} reached this suite"
    from auditmanager.api.app import create_asgi_app

    app = create_asgi_app(environ=dict(os.environ) | {
        "AUDITMANAGER_PROVIDER_MODE": "recorded",
        API_TOKEN_VARIABLE: DEPLOYMENT_SECRET,
    })
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(scope="module")
def expert() -> dict[str, str]:
    from am_test_accounts import provisioned_credential

    token = provisioned_credential(DEPLOYMENT_SECRET, "w60-price-list-expert")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def admin() -> dict[str, str]:
    """An administrator who is not an expert: the suite's account, its expert role swapped."""
    from am_test_accounts import provisioned_credential, provisioned_record

    from auditmanager.access.public import AccountRepository

    record = provisioned_record("w60-price-list-admin")
    engine = create_engine(os.environ["DATABASE_URL"])
    try:
        with Session(engine) as session:
            accounts = AccountRepository()
            if accounts.roles_of(session, str(record.user_uid)) != frozenset({"admin"}):
                seed = session.execute(
                    text("SELECT user_uid FROM app_user WHERE login = 'admin'")
                ).scalar_one()
                accounts.set_roles(
                    session, actor_uid=str(seed), user_uid=str(record.user_uid),
                    roles=frozenset({"admin"}),
                )
            session.commit()
    finally:
        engine.dispose()
    token = provisioned_credential(DEPLOYMENT_SECRET, "w60-price-list-admin")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def project(client: TestClient, expert: dict[str, str]) -> str:
    answer = client.post(
        "/projects",
        json={"name": f"Оптимизация {secrets.token_hex(4)}"},
        headers=expert | {"Idempotency-Key": f"w60-project-{secrets.token_hex(8)}"},
    )
    assert answer.status_code == 201, answer.content
    return answer.json()["project_uid"]


def _upload(client: TestClient, headers: dict[str, str], project: str, content: bytes, key: str,
            name: str = "Прайс 2026.csv") -> Any:
    return client.post(
        f"/projects/{project}/price-lists",
        files={"file": (name, content, "text/csv")},
        data={"default_currency": "RUB"},
        headers=headers | {"Idempotency-Key": key},
    )


@pytest.fixture(scope="module")
def uploaded(client: TestClient, expert: dict[str, str], project: str) -> dict[str, Any]:
    key = f"w60-upload-{secrets.token_hex(8)}"
    answer = _upload(client, expert, project, PRICE_LIST, key)
    assert answer.status_code == 201, answer.content
    assert answer.headers.get("X-Correlation-Id")
    return {"key": key, "body": answer.json()}


def test_the_upload_answers_the_revision_and_its_exact_repeat(
    client: TestClient, expert: dict[str, str], project: str, uploaded: dict[str, Any]
) -> None:
    body = uploaded["body"]
    _exact_keys(body, "PriceListRevision")
    assert body["project_uid"] == project and body["revision_number"] == 1 and body["is_current"]
    assert (body["source_format"], body["media_type"]) == ("csv", "text/csv")
    assert (body["data_row_count"], body["accepted_row_count"], body["skipped_row_count"]) == (3, 2, 1)
    assert body["default_currency"] == "RUB" and body["size_bytes"] == len(PRICE_LIST)

    again = _upload(client, expert, project, PRICE_LIST, uploaded["key"])
    assert again.status_code == 201 and again.json()["price_list_id"] == body["price_list_id"]
    other = _upload(client, expert, project, PRICE_LIST + b"x;y;z;1;;\n", uploaded["key"])
    assert other.status_code == 409 and other.json()["error_code"] == "idempotency_key_reuse"


def test_a_file_that_is_not_a_price_list_is_refused_with_its_reason(
    client: TestClient, expert: dict[str, str], admin: dict[str, str], project: str
) -> None:
    xls = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 64
    refused = _upload(client, expert, project, xls, f"w60-xls-{secrets.token_hex(8)}", "old.xls")
    assert refused.status_code == 422, refused.content
    envelope = refused.json()
    assert envelope["error_code"] == "validation_failed"
    assert envelope["details"]["field"] == "content"
    assert envelope["details"]["constraint"] == "price_list_format"

    forbidden = _upload(client, admin, project, PRICE_LIST, f"w60-admin-{secrets.token_hex(8)}")
    assert forbidden.status_code == 403 and forbidden.json()["error_code"] == "permission_denied"
    missing = _upload(client, expert, UNKNOWN_PROJECT, PRICE_LIST, f"w60-404-{secrets.token_hex(8)}")
    assert missing.status_code == 404


def test_the_revisions_and_the_positions_page(
    client: TestClient, expert: dict[str, str], project: str, uploaded: dict[str, Any]
) -> None:
    listing = client.get(f"/projects/{project}/price-lists", headers=expert)
    assert listing.status_code == 200, listing.content
    _exact_keys(listing.json(), "PriceListRevisionList")
    assert [item["price_list_id"] for item in listing.json()["items"]] == [
        uploaded["body"]["price_list_id"]
    ]

    page = client.get(
        f"/price-lists/{uploaded['body']['price_list_id']}/positions?offset=0&limit=1",
        headers=expert,
    )
    assert page.status_code == 200, page.content
    body = page.json()
    _exact_keys(body, "PriceListPositionPage")
    assert (body["total"], body["offset"], body["limit"], body["next_offset"]) == (2, 0, 1, 1)
    position = body["items"][0]
    _exact_keys(position, "PriceListPosition")
    assert (position["row_number"], position["unit_price"], position["currency"]) == (2, "125.5", "RUB")
    assert (position["section_code"], position["vendor"]) == ("EOM", "Кабельный завод")
    report = body["parse_report"]
    _exact_keys(report, "PriceListParseReport")
    assert [column["field"] for column in report["columns"]] == [
        "name", "unit", "unit_price", "code", "vendor", "section",
    ]
    assert report["skipped"] == [{"row": 3, "reason": "price_not_a_number"}]
    assert report["skipped_by_reason"] == [{"reason": "price_not_a_number", "count": 1}]
    assert report["currency_sources"] == [{"source": "price_header", "count": 2}]
    assert report["encoding"] == "cp1251" and report["delimiter"] == ";"

    second = client.get(
        f"/price-lists/{uploaded['body']['price_list_id']}/positions?offset=1&limit=1",
        headers=expert,
    ).json()
    assert second["items"][0]["unit_price"] == "12345.67" and second["next_offset"] is None
    assert client.get(f"/price-lists/{UNKNOWN_PRICE_LIST}/positions", headers=expert).status_code == 404
    assert client.get(f"/projects/{UNKNOWN_PROJECT}/price-lists", headers=expert).status_code == 404
    assert client.get(
        f"/price-lists/{uploaded['body']['price_list_id']}/positions?limit=501", headers=expert
    ).status_code == 422


def test_vendor_lists_global_and_per_project(
    client: TestClient, expert: dict[str, str], admin: dict[str, str], project: str
) -> None:
    section = "SS"
    before = client.get(f"/projects/{project}/vendor-lists", headers=expert)
    assert before.status_code == 200, before.content
    _exact_keys(before.json(), "EffectiveVendorLists")
    items = before.json()["items"]
    assert len(items) == 15
    current_global = next(item for item in items if item["section_code"] == section)["global_revision"]

    entries = [{"material": "Кабель слаботочный", "vendor": f"Завод {secrets.token_hex(3)}"}]
    refused = client.put(f"/vendor-lists/{section}", json={"entries": entries}, headers=expert)
    assert refused.status_code == 403 and refused.json()["details"]["required_capability"] == "role:admin"

    expected = None if current_global is None else current_global["vendor_list_id"]
    set_global = client.put(
        f"/vendor-lists/{section}",
        json={"entries": entries, "expected_vendor_list_id": expected},
        headers=admin,
    )
    assert set_global.status_code == 200, set_global.content
    revision = set_global.json()
    _exact_keys(revision, "VendorListRevision")
    assert (revision["scope"], revision["project_uid"], revision["mode"]) == ("global", None, "list")
    _exact_keys(revision["entries"][0], "VendorListEntry")
    assert revision["entries"][0]["note"] is None

    stale = client.put(
        f"/vendor-lists/{section}",
        json={"entries": [], "expected_vendor_list_id": expected},
        headers=admin,
    )
    assert stale.status_code == 409, stale.content
    assert stale.json()["details"]["conflict_reason"] == "vendor_list_changed"

    override = client.put(
        f"/projects/{project}/vendor-lists/{section}",
        json={"mode": "list", "entries": [{"vendor": "Проектный поставщик"}]},
        headers=expert,
    )
    assert override.status_code == 200, override.content
    state = override.json()
    _exact_keys(state, "SectionVendorList")
    assert state["source"] == "project"
    assert state["effective"]["entries"] == [
        {"material": None, "vendor": "Проектный поставщик", "note": None}
    ]
    assert state["global_revision"]["vendor_list_id"] == revision["vendor_list_id"]

    inherit = client.put(
        f"/projects/{project}/vendor-lists/{section}",
        json={"mode": "inherit", "entries": []},
        headers=expert,
    ).json()
    assert inherit["source"] == "global" and inherit["project_revision"]["mode"] == "inherit"
    bad = client.put(
        f"/projects/{project}/vendor-lists/{section}",
        json={"mode": "inherit", "entries": [{"vendor": "x"}]},
        headers=expert,
    )
    assert bad.status_code == 422 and bad.json()["details"]["constraint"] == "inherit_has_no_entries"
    by_admin = client.put(
        f"/projects/{project}/vendor-lists/{section}",
        json={"mode": "list", "entries": []},
        headers=admin,
    )
    assert by_admin.status_code == 403
    assert client.get(f"/projects/{UNKNOWN_PROJECT}/vendor-lists", headers=expert).status_code == 404
    # A section outside the fifteen addresses no vendor list: `404`, like a malformed identity.
    for path, body, headers in (
        (f"/projects/{project}/vendor-lists/XX", {"mode": "list", "entries": []}, expert),
        ("/vendor-lists/XX", {"entries": []}, admin),
    ):
        unknown = client.put(path, json=body, headers=headers)
        assert unknown.status_code == 404, unknown.content
        assert unknown.json()["details"] == {"aggregate_type": "VendorList"}
