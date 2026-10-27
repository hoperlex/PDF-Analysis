"""`ANALYSIS-PRESETS-01`: the four operations over the served application, behind the real seam.

Drives ``build_router(executors=ExecutorAdapter(...))`` through the real middlewares and the role
register (``tests/integration/api/driver.py``), so the statuses, the envelope, the optional fields and
the access rule are what a caller sees. The role sweep over every operation is
``tests/integration/api/test_role_register.py``; this file drives the behaviour behind it.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import text

from tests.integration.executors.conftest import ADMIN, build_surface, driver

Request, dispatch = driver.Request, driver.dispatch


def call(surface, method: str, path: str, body: Any = None, *, keyed: bool = True, key: str | None = None):
    headers = {"Content-Type": "application/json"}
    if keyed:
        headers["Idempotency-Key"] = key or f"preset-{uuid4().hex}"
    payload = b"" if body is None else json.dumps(body).encode()
    return dispatch(surface, Request.build(method, path, headers=headers, body=payload))


def connection(surface, name: str = "Прокси") -> str:
    created = call(surface, "POST", "/executor-connections", {"kind": "http_api", "display_name": name})
    assert created.status == 201, created.body
    return created.json()["connection_id"]


def test_the_journey_has_the_ruled_statuses_shapes_and_no_null(surface, session) -> None:
    c = connection(surface)
    created = call(surface, "POST", "/analysis/presets", {"name": "  Быстрый черновик ", "executor_connection_id": c})
    assert created.status == 201, created.body
    first = created.json()
    assert set(first) == {"preset_id", "revision_id", "revision_no", "name", "executor_connection_id",
                          "state", "created_at", "revised_at", "revised_by"}
    assert (first["revision_no"], first["state"], first["name"]) == (1, "active", "Быстрый черновик")
    assert first["preset_id"] == first["revision_id"] and first["revised_by"] == ADMIN
    assert None not in first.values()

    d = connection(surface, "Второй")
    revised = call(surface, "POST", f"/analysis/presets/{first['preset_id']}/revisions",
                   {"name": "Быстрый черновик", "executor_connection_id": d})
    assert revised.status == 201, revised.body
    second = revised.json()
    assert (second["preset_id"], second["revision_no"], second["executor_connection_id"]) == (
        first["preset_id"], 2, d)
    assert second["revision_id"] != first["revision_id"] and second["created_at"] == first["created_at"]

    listed = call(surface, "GET", "/analysis/presets", keyed=False)
    assert listed.status == 200
    assert listed.json() == {"items": [second]}, "the list shows the current revision only"

    archived = call(surface, "POST", f"/analysis/presets/{first['preset_id']}/archive")
    assert archived.status == 200, archived.body
    assert (archived.json()["revision_no"], archived.json()["state"]) == (3, "archived")
    assert archived.json()["name"] == second["name"] and archived.json()["executor_connection_id"] == d
    assert call(surface, "GET", "/analysis/presets", keyed=False).json()["items"][0]["state"] == "archived"


def test_the_event_of_every_write_is_in_the_journal_with_the_revisions_id(surface, session) -> None:
    c = connection(surface)
    made = call(surface, "POST", "/analysis/presets", {"name": "Основной", "executor_connection_id": c}).json()
    revised = call(surface, "POST", f"/analysis/presets/{made['preset_id']}/revisions",
                   {"name": "Основной 2", "executor_connection_id": c}).json()
    archived = call(surface, "POST", f"/analysis/presets/{made['preset_id']}/archive").json()
    rows = session.execute(text(
        "SELECT audit_event_id, event_type FROM audit_event WHERE aggregate_id = :p ORDER BY sequence_no"),
        {"p": made["preset_id"]}).all()
    assert [tuple(r) for r in rows] == [
        (made["revision_id"], "executor.preset_created"),
        (revised["revision_id"], "executor.preset_revised"),
        (archived["revision_id"], "executor.preset_archived")]


def test_an_expert_reads_and_is_refused_every_write(session, admin_account, rings) -> None:
    admin = build_surface(session, rings.public, roles=frozenset({"admin"}))
    c = connection(admin)
    made = call(admin, "POST", "/analysis/presets", {"name": "Основной", "executor_connection_id": c}).json()
    expert = build_surface(session, rings.public, roles=frozenset({"expert"}))
    assert call(expert, "GET", "/analysis/presets", keyed=False).json()["items"][0]["preset_id"] == made["preset_id"]
    for method, path, body in (
        ("POST", "/analysis/presets", {"name": "Иной", "executor_connection_id": c}),
        ("POST", f"/analysis/presets/{made['preset_id']}/revisions", {"name": "Иной", "executor_connection_id": c}),
        ("POST", f"/analysis/presets/{made['preset_id']}/archive", None),
    ):
        refused = call(expert, method, path, body)
        assert refused.status == 403, (path, refused.body)
        assert refused.json()["error_code"] == "permission_denied"
        assert refused.json()["details"] == {"required_capability": "role:admin"}
    assert len(call(admin, "GET", "/analysis/presets", keyed=False).json()["items"]) == 1


def test_a_write_needs_its_idempotency_key_and_a_replay_answers_the_same_body(surface) -> None:
    c = connection(surface)
    body = {"name": "Основной", "executor_connection_id": c}
    assert call(surface, "POST", "/analysis/presets", body, keyed=False).status == 422
    key = f"preset-{uuid4().hex}"
    first = call(surface, "POST", "/analysis/presets", body, key=key)
    again = call(surface, "POST", "/analysis/presets", body, key=key)
    assert (first.status, again.status) == (201, 201) and first.json() == again.json()
    assert len(call(surface, "GET", "/analysis/presets", keyed=False).json()["items"]) == 1
    reuse = call(surface, "POST", "/analysis/presets", {**body, "name": "Другое"}, key=key)
    assert reuse.status == 409 and reuse.json()["error_code"] == "idempotency_key_reuse"


@pytest.mark.parametrize(("body", "details"), [
    ({"name": "   "}, {"field": "name", "constraint": "required"}),
    ({"name": "Я" * 121}, None),  # the closed schema refuses it before the command (422 either way)
    ({"name": "А\tБ"}, {"field": "name", "constraint": "printable"}),
    ({"executor_connection_id": "exc_01M2545JSD15ETSNNV904X991N"},
     {"field": "executor_connection_id", "constraint": "unknown_connection"}),
])
def test_a_refused_save_is_a_422_on_the_field_and_writes_nothing(surface, body, details) -> None:
    c = connection(surface)
    full = {"name": "Основной", "executor_connection_id": c, **body}
    answer = call(surface, "POST", "/analysis/presets", full)
    assert answer.status == 422, answer.body
    assert answer.json()["error_code"] == "validation_failed"
    if details is not None:
        assert answer.json()["details"] == details
    assert call(surface, "GET", "/analysis/presets", keyed=False).json() == {"items": []}


def test_the_conflicts_are_409_with_their_reason(surface) -> None:
    c = connection(surface)
    made = call(surface, "POST", "/analysis/presets", {"name": "Чертежи", "executor_connection_id": c}).json()
    taken = call(surface, "POST", "/analysis/presets", {"name": "чертежи", "executor_connection_id": c})
    assert taken.status == 409 and taken.json()["details"] == {
        "conflict_reason": "preset_name_in_use", "aggregate_type": "AnalysisPreset"}
    assert call(surface, "POST", f"/analysis/presets/{made['preset_id']}/archive").status == 200
    for path, body in ((f"/analysis/presets/{made['preset_id']}/archive", None),
                       (f"/analysis/presets/{made['preset_id']}/revisions",
                        {"name": "Новое", "executor_connection_id": c})):
        gone = call(surface, "POST", path, body)
        assert gone.status == 409 and gone.json()["details"]["conflict_reason"] == "preset_archived"


def test_an_unknown_or_malformed_preset_id_is_a_404_like_every_path_identity(surface) -> None:
    c = connection(surface)
    ghost = "evt_01M2545JSD15ETSNNV904X991N"
    assert call(surface, "POST", f"/analysis/presets/{ghost}/archive").status == 404
    assert call(surface, "POST", f"/analysis/presets/{ghost}/revisions",
                {"name": "Имя", "executor_connection_id": c}).status == 404
    # a path identity of the wrong shape names nothing the caller may see, as everywhere on the surface
    assert call(surface, "POST", "/analysis/presets/not-an-id/archive").status == 404
    assert call(surface, "POST", f"/analysis/presets/{c}/archive").status == 404  # a connection id is not a preset id


def test_no_body_carries_a_secret_an_address_or_a_cost_limit(surface) -> None:
    c = connection(surface)
    made = call(surface, "POST", "/analysis/presets", {"name": "Основной", "executor_connection_id": c})
    listed = call(surface, "GET", "/analysis/presets", keyed=False)
    for answer in (made, listed):
        text_ = answer.body.decode().lower()
        for word in ("secret", "base_url", "api_key", "cost", "limit", "threshold", "ceiling"):
            assert word not in text_, word
