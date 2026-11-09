"""`DECISION-MEMORY-M2` (contract 1.44.0): the five operations over HTTP, with the shipped router and the shipped adapter, on a clone of the
migrated schema.

The security seam is not rebuilt here (``test_role_register`` and ``test_authorization`` hold the roles of all 323 operations): the subject is
supplied by overriding the dependency, and the question is what the operations DO. Shown: the list pages by cursor and filters by every
parameter; one case answers its content, decisions, evidence, norm references, crops and history; the status answers the counts and the
settings in force; a withdraw and a restore are keyed (an exact repeat answers the first event, another payload under the key is
``idempotency_key_reuse``, a missing key and a bad reason or identity are ``422``); a transition the case is not in is
``409 state_transition_not_allowed``; an unknown case is ``404``; a FORGOTTEN case answers its tombstone only and takes no status event
(``409 conflict``, ``memory_case_forgotten``); and every answer carries exactly the properties of its contract schema.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi import APIRouter, FastAPI
from sqlalchemy import Engine, text
from sqlalchemy.orm import sessionmaker
from starlette.testclient import TestClient

from auditmanager.api.routers.decision_memory import build_decision_memory_routes
from auditmanager.api.routers.handlers import install_exception_handlers
from auditmanager.api.security import Subject, current_subject
from auditmanager.bootstrap.adapters import DecisionMemoryAdapter
from auditmanager.shared.db.engine import create_database_engine
from tests.support.memory_seed import ensure_blob, seed_case

CONTRACT = Path(__file__).resolve().parents[3] / "contracts" / "api" / "v1" / "openapi.json"
BLOB = "blob_01ARZ3NDEKTSV4RRFFQ69G5FAV"
PROJECT_A = "prj_01ARZ3NDEKTSV4RRFFQ69G5FAA"
PROJECT_B = "prj_01ARZ3NDEKTSV4RRFFQ69G5FAB"
UNKNOWN = "dmc_01ARZ3NDEKTSV4RRFFQ69G5FAV"
BASE = "/decision-memory"


def _properties(schema: str) -> set[str]:
    return set(json.loads(CONTRACT.read_text(encoding="utf-8"))["components"]["schemas"][schema]["properties"])


@pytest.fixture
def served(migrated_database: Any) -> Iterator[tuple[TestClient, Engine, dict[str, str], str]]:
    engine = create_database_engine(migrated_database)
    with engine.begin() as connection:
        ensure_blob(connection, BLOB)
        admin = str(connection.execute(text("SELECT user_uid FROM app_user WHERE login = 'admin'")).scalar_one())
        a = seed_case(connection, project=PROJECT_A, blob=BLOB, verdicts=("accept", "reject"))["case_id"]
        b = seed_case(connection, project=PROJECT_B)["case_id"]
        forgotten = seed_case(connection, project=PROJECT_A)["case_id"]
    router = APIRouter()
    build_decision_memory_routes(router, DecisionMemoryAdapter(sessionmaker(bind=engine, expire_on_commit=False, future=True)))
    app = FastAPI(servers=[{"url": "/api/v1"}], separate_input_output_schemas=False)
    app.include_router(router, prefix="/api/v1")
    install_exception_handlers(app)
    app.dependency_overrides[current_subject] = lambda: Subject(
        user_uid=admin, login="admin", token_epoch=1, display_label="admin")
    # a forget, the way the operator tool writes it: the event and the deletes in one transaction
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO decision_memory_status_event (status_event_id, case_id, kind, reason_code, actor_user_uid, owner_permission_ref, "
            "forgotten_content_sha256) SELECT 'dmw_01ARZ3NDEKTSV4RRFFQ69G5FAV', case_id, 'forget', 'client_request', :a, 'owner message', "
            "content_sha256 FROM decision_memory_case WHERE case_id = :c"), {"a": admin, "c": forgotten})
        for table in ("decision_memory_evidence", "decision_memory_norm_ref", "decision_memory_crop"):
            connection.execute(text(f"DELETE FROM {table} WHERE case_id = :c"), {"c": forgotten})
        connection.execute(text("DELETE FROM decision_memory_decision_text WHERE memory_decision_id IN "
                                "(SELECT memory_decision_id FROM decision_memory_decision WHERE case_id = :c)"), {"c": forgotten})
        connection.execute(text("DELETE FROM decision_memory_content WHERE case_id = :c"), {"c": forgotten})
    try:
        yield TestClient(app, raise_server_exceptions=False), engine, {"a": a, "b": b, "forgotten": forgotten}, admin
    finally:
        engine.dispose()


def _key(value: str) -> dict[str, str]:
    return {"Idempotency-Key": value}


def test_the_list_pages_by_cursor_and_filters_by_every_parameter(served: Any) -> None:
    client, _, cases, _ = served
    everything = client.get(f"/api/v1{BASE}/cases")
    assert everything.status_code == 200, everything.text
    body = everything.json()
    assert set(body) == _properties("DecisionMemoryCasePage") and set(body["page"]) == {"next_cursor"}
    assert {c["case_id"] for c in body["items"]} == set(cases.values())
    assert all(set(item) == _properties("DecisionMemoryCaseSummary") for item in body["items"])
    by_id = {c["case_id"]: c for c in body["items"]}
    assert (by_id[cases["a"]]["decision_count"], by_id[cases["a"]]["current_verdict"], by_id[cases["a"]]["status"]) == (2, "rejected", "active")
    assert by_id[cases["forgotten"]]["status"] == "forgotten"

    first = client.get(f"/api/v1{BASE}/cases", params={"limit": 2}).json()
    assert len(first["items"]) == 2 and first["page"]["next_cursor"]
    rest = client.get(f"/api/v1{BASE}/cases", params={"limit": 2, "cursor": first["page"]["next_cursor"]}).json()
    assert len(rest["items"]) == 1 and rest["page"]["next_cursor"] is None
    assert {c["case_id"] for c in first["items"] + rest["items"]} == set(cases.values())

    for params, expected in [
        ({"status": "forgotten"}, {cases["forgotten"]}), ({"status": "withdrawn"}, set()),
        ({"origin_project_uid": PROJECT_B}, {cases["b"]}), ({"verdict": "rejected"}, {cases["a"]}),
        ({"section_code": "AR", "category": "internal_contradiction", "data_class": "test", "origin_project_uid": PROJECT_A},
         {cases["a"], cases["forgotten"]}), ({"data_class": "real"}, set()), ({"section_code": "KJ"}, set()),
        ({"status": ""}, set(cases.values())),        # an empty filter is the absent one
    ]:
        answer = client.get(f"/api/v1{BASE}/cases", params=params)
        assert answer.status_code == 200, (params, answer.text)
        assert {c["case_id"] for c in answer.json()["items"]} == expected, params
    for params in ({"status": "gone"}, {"verdict": "maybe"}, {"data_class": "production"}, {"limit": 0}, {"origin_project_uid": "x"},
                   {"cursor": "not-a-cursor"}):
        answer = client.get(f"/api/v1{BASE}/cases", params=params)
        assert answer.status_code == 422, (params, answer.status_code, answer.text)


def test_one_case_answers_what_it_keeps_and_a_forgotten_case_its_tombstone_only(served: Any) -> None:
    client, _, cases, admin = served
    answer = client.get(f"/api/v1{BASE}/cases/{cases['a']}")
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert set(body) == _properties("DecisionMemoryCase")
    assert body["summary"]["case_id"] == cases["a"] and body["content"]["finding_text"] == "finding"
    assert set(body["content"]) == _properties("DecisionMemoryContent")
    assert [(d["event_type"], d["comment"]) for d in body["decisions"]] == [("accept", "the expert wrote this"), ("reject", "the expert wrote this")]
    assert all(set(d) == _properties("DecisionMemoryDecision") for d in body["decisions"])
    assert [e["quote"] for e in body["evidence"]] == ["quote"] and set(body["evidence"][0]) == _properties("DecisionMemoryEvidence")
    assert body["evidence"][0]["bbox"] is None
    assert body["norm_refs"][0]["designation"] == "SP 1" and set(body["norm_refs"][0]) == _properties("DecisionMemoryNormRef")
    crop = body["crops"][0]
    assert set(crop) == _properties("DecisionMemoryCrop") and crop["bbox"] == [0.1, 0.1, 0.5, 0.5] and crop["media_type"] == "image/png"
    assert "blob_id" not in json.dumps(body) and "actor_user_uid" not in json.dumps(body)       # no storage identity, no account

    tomb = client.get(f"/api/v1{BASE}/cases/{cases['forgotten']}").json()
    assert tomb["summary"]["status"] == "forgotten" and tomb["content"] is None
    assert tomb["evidence"] == [] and tomb["norm_refs"] == [] and tomb["crops"] == []
    assert [d["comment"] for d in tomb["decisions"]] == [None]                       # the verdict stays, the words do not
    (event,) = tomb["status_events"]
    assert set(event) == _properties("DecisionMemoryStatusEvent") and event["kind"] == "forget"
    assert event["forgotten_content_sha256"] == "a" * 64 and "owner" not in json.dumps(tomb)

    assert client.get(f"/api/v1{BASE}/cases/{UNKNOWN}").status_code == 404
    assert client.get(f"/api/v1{BASE}/cases/not-a-case").status_code == 404      # a malformed identity in a path is "not found", as everywhere


def test_the_status_answers_the_counts_and_the_settings_in_force(served: Any) -> None:
    client, engine, _, admin = served
    body = client.get(f"/api/v1{BASE}/status").json()
    assert set(body) == _properties("DecisionMemoryStatus")
    assert (body["data_class"], body["training_use"], body["cases"], body["decisions"]) == ("test", "off", 3, 4)
    assert all(set(row) == _properties("DecisionMemoryCountRow") for row in body["by_status_and_class"])
    assert {(r["status"], r["data_class"], r["cases"]) for r in body["by_status_and_class"]} == {("active", "test", 2), ("forgotten", "test", 1)}
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO decision_memory_setting_event (setting_name, revision, value, actor_user_uid) "
                                "VALUES ('data_class', 1, 'real', :a)"), {"a": admin})
    assert client.get(f"/api/v1{BASE}/status").json()["data_class"] == "real"


def test_withdraw_and_restore_are_keyed_typed_and_append_only(served: Any) -> None:
    client, engine, cases, admin = served
    url = f"/api/v1{BASE}/cases/{cases['b']}"
    first = client.post(f"{url}/withdraw", json={"reason_code": "wrong_decision"}, headers=_key("key-http-withdraw-1"))
    assert first.status_code == 200, first.text
    change = first.json()
    assert set(change) == _properties("DecisionMemoryStatusChange")
    assert (change["case_id"], change["kind"], change["status"], change["reason_code"]) == (cases["b"], "withdraw", "withdrawn", "wrong_decision")
    assert client.get(f"/api/v1{BASE}/cases/{cases['b']}").json()["summary"]["status"] == "withdrawn"

    replay = client.post(f"{url}/withdraw", json={"reason_code": "wrong_decision"}, headers=_key("key-http-withdraw-1"))
    assert replay.status_code == 200 and replay.json() == change                          # the first call's event, nothing written
    reuse = client.post(f"{url}/withdraw", json={"reason_code": "other"}, headers=_key("key-http-withdraw-1"))
    assert reuse.status_code == 409 and reuse.json()["error_code"] == "idempotency_key_reuse", reuse.text
    again = client.post(f"{url}/withdraw", json={"reason_code": "other"}, headers=_key("key-http-withdraw-2"))
    assert again.status_code == 409 and again.json()["error_code"] == "state_transition_not_allowed", again.text

    restored = client.post(f"{url}/restore", json={"reason_code": "other"}, headers=_key("key-http-restore-1"))
    assert restored.status_code == 200 and (restored.json()["kind"], restored.json()["status"]) == ("restore", "active")
    nothing = client.post(f"{url}/restore", json={"reason_code": "other"}, headers=_key("key-http-restore-2"))
    assert nothing.status_code == 409 and nothing.json()["error_code"] == "state_transition_not_allowed"
    history = client.get(f"/api/v1{BASE}/cases/{cases['b']}").json()["status_events"]
    assert [e["kind"] for e in history] == ["withdraw", "restore"]
    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM decision_memory_status_event WHERE case_id = :c AND command_id IS NOT NULL"),
                                  {"c": cases["b"]}).scalar_one() == 2                  # each names its receipt


def test_the_refusals_of_the_writes(served: Any) -> None:
    client, _, cases, _ = served
    url = f"/api/v1{BASE}/cases/{cases['b']}"
    assert client.post(f"{url}/withdraw", json={"reason_code": "other"}).status_code == 422                   # no Idempotency-Key
    assert client.post(f"{url}/withdraw", json={"reason_code": "because I said so"}, headers=_key("key-http-bad-reason")).status_code == 422
    assert client.post(f"{url}/withdraw", json={}, headers=_key("key-http-no-reason")).status_code == 422
    assert client.post(f"{url}/withdraw", json={"reason_code": "other", "extra": 1}, headers=_key("key-http-extra")).status_code == 422
    assert client.post(f"/api/v1{BASE}/cases/not-a-case/withdraw", json={"reason_code": "other"}, headers=_key("key-http-bad-id")).status_code == 404
    unknown = client.post(f"/api/v1{BASE}/cases/{UNKNOWN}/restore", json={"reason_code": "other"}, headers=_key("key-http-unknown"))
    assert unknown.status_code == 404
    for verb in ("withdraw", "restore"):
        forgotten = client.post(f"/api/v1{BASE}/cases/{cases['forgotten']}/{verb}", json={"reason_code": "other"}, headers=_key(f"key-http-forgot-{verb}"))
        assert forgotten.status_code == 409, forgotten.text
        envelope = forgotten.json()
        assert envelope["error_code"] == "conflict" and envelope["details"]["conflict_reason"] == "memory_case_forgotten", envelope
