"""`W60-OPT-PROPOSALS-01`, end to end: the six «Предложения» operations over HTTP.

The composed ASGI application (``create_asgi_app``) with the recorded provider, against the
lane's own PostgreSQL and MinIO, driven with real credentials -- an expert, and an
administrator who is not an expert. One portal bundle is uploaded; then, in the order the
operation checks them, every refusal of ``startOptimisationPass`` appears as its input does:
``version_unclassified``, ``section_not_ar`` (a second set), ``price_list_missing``,
``analysis_missing`` (before the recorded run publishes), ``vendor_list_missing``. Each is
``409 conflict`` with its ``conflict_reason`` and leaves nothing behind.

The shipped adapter reads the run's saved text from MinIO, held to the digest its stage row
recorded; the baseline document has no specification table, so the saved page text of the
published run is replaced here -- and only here, through the adapter's own reader class -- by
one Form-7 page with real rows. Everything else is the shipped path: the specification read,
the matching, the generator, the schema's triggers, the decisions, the CSV.

What is held: ``201`` with the pass pinned to its inputs, the exact repeat of the key answered
with the same pass, a new key over the same inputs answered with the stored pass, an
administrator alone ``403`` on both writes, the proposals page with exact prices and a saving
only where the quantity is a number, decisions appended with their history and counts by
decision, ``revise`` without a comment ``422``, the CSV (BOM, header, one row per proposal,
formula-escaped), every object carrying exactly its frozen schema's properties, and ``404`` for
what does not exist or belongs to another project.

The lane database persists between runs, so every run works in a project of its own and keys
of its own.
"""

from __future__ import annotations

import json
import os
import secrets
import uuid
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from auditmanager.api.routers.idempotency import IDEMPOTENCY_HEADER
from auditmanager.api.security import API_TOKEN_VARIABLE

DEPLOYMENT_SECRET = "w60-opt-proposals-over-http-token"
EXPERT = "w60-opt-proposals-expert"
ADMIN = "w60-opt-proposals-admin"
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
BASELINE_BUNDLE = REPOSITORY_ROOT / "fixtures" / "synthetic" / "ar" / "bundles" / "ar_baseline.zip"
CONTRACT = REPOSITORY_ROOT / "contracts" / "api" / "v1" / "openapi.json"
UNKNOWN_PROJECT = "prj_01M2545JSD15ETSNNV904X991F"
UNKNOWN_PASS = "opp_01M2545JSD15ETSNNV904X991N"
UNKNOWN_PROPOSAL = "opr_01M2545JSD15ETSNNV904X991N"
HOSTILE_VENDOR = '=HYPERLINK("http://example.invalid")'

FORM7_PAGE = (
    "Поз. Наименование и техническая характеристика Тип, марка Код Завод- Ед. Кол. Масса Примечание\n"
    "изготовитель изм. 1 ед., кг\n"
    "1 Дверь противопожарная ДПМ-01/60 ООО «Промет» шт. 4 45,5\n"
    "2 Анкер химический HIT-HY 200 шт 200\n"
    "3 Монтажная лента компл. - по месту\n"
)
PRICE_LIST = (
    "Код;Наименование;Марка;Ед. изм.;Цена;Валюта;Поставщик\n"
    ";Дверь противопожарная;ДПМ-01/60;шт;25000;RUB;ООО «Промет»\n"
    ";Дверь противопожарная;ДПМ-02/60;шт;21000;RUB;Кнауф Гипс\n"
    ";Дверь противопожарная металлическая;;шт;19500;RUB;Неизвестный завод\n"
    ";Анкер химический;HIT-HY 200;шт;12,75;EUR;Промет\n"
    f";Анкер химический;HIT-HY 170;шт;9,5;EUR;\"{HOSTILE_VENDOR.replace(chr(34), chr(34) * 2)}\"\n"
    ";Монтажная лента;;компл;450;RUB;Промет\n"
    ";Монтажная лента армированная;;компл;300;RUB;Кнауф Гипс\n"
).encode("utf-8")
VENDORS = [{"vendor": "Кнауф Гипс"}, {"vendor": HOSTILE_VENDOR}, {"vendor": "Промет"}]


def _schema(name: str) -> dict[str, Any]:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))["components"]["schemas"][name]


def _exact_keys(body: dict[str, Any], schema: str) -> None:
    assert set(body) == set(_schema(schema)["properties"]), schema


@pytest.fixture(scope="module")
def app_and_client() -> tuple[Any, TestClient]:
    assert os.environ.get("DATABASE_URL"), "this suite needs the lane's .env loaded"
    for leaked in ("ANTHROPIC_API_KEY", "PROXY_LLM_BASE_URL", "PROXY_LLM_TOKEN"):
        assert leaked not in os.environ, f"{leaked} reached this suite"
    from auditmanager.api.app import create_asgi_app

    app = create_asgi_app(environ=dict(os.environ) | {
        "AUDITMANAGER_PROVIDER_MODE": "recorded",
        API_TOKEN_VARIABLE: DEPLOYMENT_SECRET,
    })
    return app, TestClient(app, raise_server_exceptions=False)


@pytest.fixture(scope="module")
def expert() -> dict[str, str]:
    from am_test_accounts import provisioned_credential

    return {"Authorization": f"Bearer {provisioned_credential(DEPLOYMENT_SECRET, EXPERT)}"}


@pytest.fixture(scope="module")
def admin() -> dict[str, str]:
    """An administrator who is not an expert: the suite's account, its expert role swapped."""
    from am_test_accounts import provisioned_credential, provisioned_record

    from auditmanager.access.public import AccountRepository

    record = provisioned_record(ADMIN)
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
    return {"Authorization": f"Bearer {provisioned_credential(DEPLOYMENT_SECRET, ADMIN)}"}


def _key(tag: str) -> dict[str, str]:
    return {IDEMPOTENCY_HEADER: f"w60p-{tag}-{secrets.token_hex(6)}"}


def _project(client: TestClient, headers: dict[str, str], tag: str) -> str:
    answer = client.post(
        "/projects", json={"name": f"W60 предложения {tag}"}, headers=headers | _key("project")
    )
    assert answer.status_code == 201, answer.content
    return answer.json()["project_uid"]


def _upload(client: TestClient, headers: dict[str, str], project_uid: str, tag: str) -> dict[str, Any]:
    boundary = "w60proposalsboundary"
    head = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
        f'filename="ar_baseline.zip"\r\nContent-Type: application/zip\r\n\r\n'
    ).encode("utf-8")
    answer = client.post(
        f"/projects/{project_uid}/documents",
        headers=headers | _key(f"upload-{tag}") | {
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        content=head + BASELINE_BUNDLE.read_bytes() + f"\r\n--{boundary}--\r\n".encode("utf-8"),
    )
    assert answer.status_code == 201, answer.content
    return answer.json()


def _classify(client: TestClient, headers: dict[str, str], project: str, uploaded: dict[str, Any],
              section: str) -> None:
    answer = client.put(
        f"/projects/{project}/documents/{uploaded['document_uid']}"
        f"/versions/{uploaded['version_uid']}/classification",
        headers=headers,
        json={"project_stage": "R", "section_code": section},
    )
    assert answer.status_code == 200, answer.content


def _price_list(client: TestClient, headers: dict[str, str], project: str) -> None:
    answer = client.post(
        f"/projects/{project}/price-lists",
        files={"file": ("Прайс.csv", PRICE_LIST, "text/csv")},
        data={"default_currency": "RUB"},
        headers=headers | _key("prices"),
    )
    assert answer.status_code == 201, answer.content


def _start(client: TestClient, headers: dict[str, str], project: str, document: str,
           key: str | None = None) -> Any:
    return client.post(
        f"/projects/{project}/documents/{document}/optimisation-passes",
        headers=headers | ({IDEMPOTENCY_HEADER: key} if key else _key("start")),
    )


@pytest.fixture(scope="module")
def world(app_and_client, expert, admin) -> dict[str, Any]:
    from auditmanager.optimisation.public import SavedPageText
    from auditmanager.bootstrap import adapters

    app, client = app_and_client
    tag = uuid.uuid4().hex[:10]
    project = _project(client, expert, tag)
    foreign_project = _project(client, expert, f"{tag}-other")
    ar = _upload(client, expert, project, f"{tag}-ar")
    kj = _upload(client, expert, project, f"{tag}-kj")
    foreign = _upload(client, expert, foreign_project, f"{tag}-foreign")

    # Every refusal, in the order the operation checks them, each leaving nothing behind.
    reasons: list[tuple[str, int]] = []

    def refused(document: dict[str, Any]) -> dict[str, Any]:
        answer = _start(client, expert, project, document["document_uid"])
        assert answer.status_code == 409, answer.content
        body = answer.json()
        assert body["error_code"] == "conflict" and body["details"]["aggregate_type"] == "OptimisationPass"
        reasons.append((body["details"]["conflict_reason"], answer.status_code))
        return body

    refused(ar)
    _classify(client, expert, project, kj, "KJ")
    refused(kj)
    _classify(client, expert, project, ar, "AR")
    refused(ar)
    _price_list(client, expert, project)
    refused(ar)
    started = client.post(
        "/runs", headers=expert | _key("run"), json={"version_uid": ar["version_uid"]},
    )
    assert started.status_code == 202, started.content
    run_id = started.json()["run_id"]
    assert app.state.run_carrier.drain(timeout=300), "the run never finished"
    assert client.get(f"/runs/{run_id}", headers=expert).json()["state"] == "published"
    # The lane database persists between runs, and a global vendor list cannot be unset: the
    # last refusal appears only on the first run, while no administrator has kept an AR list.
    current = client.get(f"/projects/{project}/vendor-lists", headers=admin).json()["items"]
    global_ar = next(item for item in current if item["section_code"] == "AR")["global_revision"]
    if global_ar is None:
        refused(ar)

    # The administrator keeps the AR vendor list; the baseline text has no specification, so
    # the saved text of the published run is replaced by one Form-7 page, through the
    # adapter's own reader class.
    set_list = client.put(
        "/vendor-lists/AR",
        json={"entries": VENDORS,
              "expected_vendor_list_id": None if global_ar is None else global_ar["vendor_list_id"]},
        headers=admin,
    )
    assert set_list.status_code == 200, set_list.content

    original = adapters._ProposalTextReader.saved_page_text

    def form7(self: Any, session: Any, *, run_id: str, version_uid: str, page_count: int) -> Any:
        real = original(self, session, run_id=run_id, version_uid=version_uid, page_count=page_count)
        pages = {number: "" for number in range(1, page_count + 1)}
        pages[1] = FORM7_PAGE
        return SavedPageText(run_id, real.text_layer_sha256, pages)

    adapters._ProposalTextReader.saved_page_text = form7  # type: ignore[method-assign]
    try:
        yield {
            "client": client, "tag": tag, "project": project, "foreign_project": foreign_project,
            "ar": ar, "kj": kj, "foreign": foreign, "run_id": run_id, "reasons": reasons,
            "vendor_list_id": set_list.json()["vendor_list_id"],
        }
    finally:
        adapters._ProposalTextReader.saved_page_text = original  # type: ignore[method-assign]


def test_every_refusal_names_the_first_unmet_precondition_in_order(world) -> None:
    expected = [
        "version_unclassified",
        "section_not_ar",
        "price_list_missing",
        "analysis_missing",
        "vendor_list_missing",
    ]
    assert [reason for reason, _ in world["reasons"]] == expected[: len(world["reasons"])]
    assert len(world["reasons"]) >= 4  # the fifth only while no AR vendor list was ever kept


@pytest.fixture(scope="module")
def started(world, expert) -> dict[str, Any]:
    key = f"w60p-started-{world['tag']}"
    answer = _start(world["client"], expert, world["project"], world["ar"]["document_uid"], key)
    assert answer.status_code == 201, answer.content
    return {"key": key, "body": answer.json()}


def test_the_pass_is_pinned_to_its_inputs_and_replays_by_key(world, expert, admin, started) -> None:
    client, body = world["client"], started["body"]
    _exact_keys(body, "OptimisationPass")
    _exact_keys(body["decision_counts"], "ProposalDecisionCounts")
    assert body["project_uid"] == world["project"] and body["document_uid"] == world["ar"]["document_uid"]
    assert body["version_uid"] == world["ar"]["version_uid"] and body["run_id"] == world["run_id"]
    assert body["vendor_list_id"] == world["vendor_list_id"] and body["vendor_list_source"] == "global"
    assert body["generator_version"] == "cheaper-analog-v1"
    assert (body["specification_row_count"], body["matched_row_count"]) == (3, 3)
    assert (body["proposed_row_count"], body["proposal_count"]) == (3, 3)
    assert body["decision_counts"] == {"pending": 3, "accept": 0, "reject": 0, "revise": 0}
    assert body["started_by_label"] and body["text_layer_sha256"] != "0" * 64

    document = world["ar"]["document_uid"]
    replay = _start(client, expert, world["project"], document, started["key"])
    assert replay.status_code == 201 and replay.json() == body
    same_inputs = _start(client, expert, world["project"], document)
    assert same_inputs.status_code == 201
    assert same_inputs.json()["optimisation_pass_id"] == body["optimisation_pass_id"]
    other_set = _start(client, expert, world["project"], world["kj"]["document_uid"], started["key"])
    assert other_set.status_code == 409 and other_set.json()["error_code"] == "idempotency_key_reuse"

    denied = _start(client, admin, world["project"], document)
    assert denied.status_code == 403 and denied.json()["details"]["required_capability"] == "role:expert"
    no_key = client.post(
        f"/projects/{world['project']}/documents/{document}/optimisation-passes", headers=expert
    )
    assert no_key.status_code == 422, no_key.content
    foreign = _start(client, expert, world["project"], world["foreign"]["document_uid"])
    assert foreign.status_code == 404 and foreign.json()["error_code"] == "not_found"
    assert _start(client, expert, UNKNOWN_PROJECT, document).status_code == 404


def test_the_passes_and_the_proposals_with_exact_prices(world, expert, admin, started) -> None:
    client, pass_id = world["client"], started["body"]["optimisation_pass_id"]
    listing = client.get(
        f"/projects/{world['project']}/optimisation-passes",
        params={"document_uid": world["ar"]["document_uid"]},
        headers=admin,
    )
    assert listing.status_code == 200, listing.content
    _exact_keys(listing.json(), "OptimisationPassList")
    assert [item["optimisation_pass_id"] for item in listing.json()["items"]] == [pass_id]
    assert client.get(f"/projects/{world['project']}/optimisation-passes", headers=expert).status_code == 200
    assert client.get(
        f"/projects/{world['project']}/optimisation-passes",
        params={"document_uid": world["foreign"]["document_uid"]}, headers=expert,
    ).status_code == 404
    assert client.get(
        f"/projects/{UNKNOWN_PROJECT}/optimisation-passes", headers=expert
    ).status_code == 404

    page = client.get(f"/optimisation-passes/{pass_id}/proposals", headers=expert)
    assert page.status_code == 200, page.content
    body = page.json()
    _exact_keys(body, "OptimisationProposalPage")
    assert (body["total"], body["offset"], body["limit"], body["next_offset"]) == (3, 0, 50, None)
    door, anchor, tape = body["items"]
    for item in body["items"]:
        _exact_keys(item, "OptimisationProposal")
        _exact_keys(item["matched_position"], "ProposalPosition")
    assert [item["ordinal"] for item in body["items"]] == [1, 2, 3]
    assert (door["current_unit_price"], door["proposed_unit_price"], door["saving"]) == (
        "25000", "21000", "16000",
    )
    assert (door["quantity"], door["unit"], door["currency"], door["proposed_vendor"]) == (
        "4", "шт", "RUB", "Кнауф Гипс",
    )
    assert (door["analog_basis"], door["matched_basis"]) == ("code_family", "mark")
    assert (anchor["currency"], anchor["saving"], anchor["proposed_vendor"]) == ("EUR", "650", HOSTILE_VENDOR)
    # The tape's quantity is a dash: both prices are shown and the saving is absent, never "0".
    assert (tape["quantity"], tape["quantity_text"], tape["saving"]) == (None, "-", None)
    assert (tape["current_unit_price"], tape["proposed_unit_price"]) == ("450", "300")
    assert tape["current_verdict"] == "pending" and tape["current_decision"] is None

    paged = client.get(
        f"/optimisation-passes/{pass_id}/proposals", params={"offset": 1, "limit": 1}, headers=expert
    ).json()
    assert (paged["total"], len(paged["items"]), paged["next_offset"]) == (3, 1, 2)
    for query in ({"limit": 0}, {"limit": 201}, {"offset": -1}, {"decision": "accepted"}):
        refused = client.get(f"/optimisation-passes/{pass_id}/proposals", params=query, headers=expert)
        assert refused.status_code == 422, (query, refused.content)
    assert client.get(f"/optimisation-passes/{UNKNOWN_PASS}/proposals", headers=expert).status_code == 404


def test_decisions_are_appended_counted_and_listed(world, expert, admin, started) -> None:
    client, pass_id = world["client"], started["body"]["optimisation_pass_id"]
    items = client.get(f"/optimisation-passes/{pass_id}/proposals", headers=expert).json()["items"]
    door, anchor, tape = (item["optimisation_proposal_id"] for item in items)
    path = f"/optimisation-proposals/{door}/decisions"

    accept = client.post(path, json={"verdict": "accept"}, headers=expert | _key("accept"))
    assert accept.status_code == 201, accept.content
    result = accept.json()
    _exact_keys(result, "ProposalDecisionResult")
    _exact_keys(result["decision"], "ProposalDecision")
    assert result["decision"]["verdict"] == "accept" and result["decision"]["comment"] is None
    assert result["proposal"]["current_verdict"] == "accept"

    key = f"w60p-revise-{world['tag']}"
    revise = client.post(
        path, json={"verdict": "revise", "comment": "  Уточнить   марку двери. "},
        headers=expert | {IDEMPOTENCY_HEADER: key},
    )
    assert revise.status_code == 201 and revise.json()["decision"]["comment"] == "Уточнить марку двери."
    replay = client.post(
        path, json={"verdict": "revise", "comment": "Уточнить марку двери."},
        headers=expert | {IDEMPOTENCY_HEADER: key},
    )
    assert replay.status_code == 201
    assert replay.json()["decision"]["proposal_decision_id"] == revise.json()["decision"]["proposal_decision_id"]
    reused = client.post(
        path, json={"verdict": "reject"}, headers=expert | {IDEMPOTENCY_HEADER: key}
    )
    assert reused.status_code == 409 and reused.json()["error_code"] == "idempotency_key_reuse"

    history = client.get(path, headers=admin)
    assert history.status_code == 200, history.content
    _exact_keys(history.json(), "ProposalDecisionList")
    assert [entry["verdict"] for entry in history.json()["items"]] == ["accept", "revise"]

    reject = client.post(
        f"/optimisation-proposals/{anchor}/decisions",
        json={"verdict": "reject", "comment": "Дороже монтаж."}, headers=expert | _key("reject"),
    )
    assert reject.status_code == 201

    for body, headers, status in (
        ({"verdict": "revise"}, expert, 422),
        ({"verdict": "revise", "comment": "   "}, expert, 422),
        ({"verdict": "pending"}, expert, 422),
        ({"verdict": "accept", "comment": "я" * 2001}, expert, 422),
        ({"verdict": "accept", "extra": 1}, expert, 422),
        ({"verdict": "accept"}, admin, 403),
    ):
        refused = client.post(f"/optimisation-proposals/{tape}/decisions", json=body,
                              headers=headers | _key("refused"))
        assert refused.status_code == status, (body, refused.content)
    missing_key = client.post(f"/optimisation-proposals/{tape}/decisions",
                              json={"verdict": "accept"}, headers=expert)
    assert missing_key.status_code == 422
    assert client.post(
        f"/optimisation-proposals/{UNKNOWN_PROPOSAL}/decisions", json={"verdict": "accept"},
        headers=expert | _key("missing"),
    ).status_code == 404
    assert client.get(
        f"/optimisation-proposals/{UNKNOWN_PROPOSAL}/decisions", headers=expert
    ).status_code == 404
    assert client.get(f"/optimisation-proposals/{tape}/decisions", headers=expert).json() == {"items": []}

    counted = client.get(f"/optimisation-passes/{pass_id}/proposals", headers=expert).json()
    assert counted["optimisation_pass"]["decision_counts"] == {
        "pending": 1, "accept": 0, "reject": 1, "revise": 1,
    }
    only = client.get(
        f"/optimisation-passes/{pass_id}/proposals", params={"decision": "revise"}, headers=expert
    ).json()
    assert [item["optimisation_proposal_id"] for item in only["items"]] == [door]
    assert only["total"] == 1 and only["decision"] == "revise"
    assert only["optimisation_pass"]["decision_counts"] == counted["optimisation_pass"]["decision_counts"]
    assert only["items"][0]["current_decision"]["comment"] == "Уточнить марку двери."


def test_the_csv_is_escaped_complete_and_separate_from_findings(world, expert, admin, started) -> None:
    client, pass_id = world["client"], started["body"]["optimisation_pass_id"]
    answer = client.get(f"/optimisation-passes/{pass_id}/export.csv", headers=admin)
    assert answer.status_code == 200, answer.content
    assert answer.headers["content-type"] == "text/csv; charset=utf-8"
    assert answer.headers["content-disposition"] == f'attachment; filename="{pass_id}.csv"'
    content = answer.content
    assert content.startswith(b"\xef\xbb\xbf") and content.count(b"\xef\xbb\xbf") == 1
    lines = content[3:].decode("utf-8").split("\r\n")
    assert lines[-1] == "" and len(lines) == 1 + 3 + 1
    assert lines[0].startswith("optimisation_pass_id,project_uid,document_uid")
    assert "'" + HOSTILE_VENDOR.replace('"', '""') in content.decode("utf-8")
    assert "run_id,run_state,provider_mode" not in lines[0]  # not the findings' file
    assert client.get(f"/optimisation-passes/{pass_id}/export.csv", headers=expert).content == content
    assert client.get(f"/optimisation-passes/{UNKNOWN_PASS}/export.csv", headers=expert).status_code == 404
    assert client.get("/optimisation-passes/opr_not_a_pass/export.csv", headers=expert).status_code == 404
