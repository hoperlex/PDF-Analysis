"""The composed application must *answer*, not merely build.

This suite exists because it was missing. `test_composition_root.py` proves the application
wires, and every other suite reaches into a module directly, so nothing drove a request
through the router. A defect sat in the adapters for the whole of Gate C's first day:
`IngestService` owns its own sessions and the adapters passed one in, which raised a
TypeError and surfaced as a 500 on the very first `POST /projects`.

It was found by driving the router once. That is the entire lesson, and these tests are the
form it takes: a smoke pass over every operation the frozen document declares, so an adapter
that cannot call its own module fails here rather than in front of a reviewer.

Session `C2` owns the ten PC-01 acceptance criteria. This is narrower on purpose - it asks
only "does each operation reach its module and come back", which is the question the
composition root itself is responsible for.
"""

from __future__ import annotations

import json
import os
import uuid
from typing import Any

import pytest

from auditmanager.api.app import create_app
from auditmanager.api.routers import dispatch
from auditmanager.api.routers.http import Request
from auditmanager.api.routers.idempotency import IDEMPOTENCY_HEADER


@pytest.fixture(scope="module")
def app() -> Any:
    assert os.environ.get("DATABASE_URL"), "this suite needs the lane's .env loaded"
    return create_app()


def _key(label: str) -> str:
    return f"{label}-{uuid.uuid4().hex[:16]}"


def call(
    app: Any,
    method: str,
    path: str,
    *,
    body: Any = None,
    key: str | None = None,
    query: dict[str, list[str]] | None = None,
) -> tuple[int, Any]:
    headers: dict[str, str] = {}
    payload = b""
    if body is not None:
        headers["content-type"] = "application/json"
        payload = json.dumps(body).encode()
    if key is not None:
        headers[IDEMPOTENCY_HEADER] = key
    response = dispatch(
        app.router,
        Request(method=method, path=path, headers=headers, query=query or {}, body=payload),
    )
    decoded: Any
    try:
        decoded = json.loads(response.body) if response.body else None
    except ValueError:
        decoded = response.body
    return response.status, decoded


class TestEveryOperationReachesItsModule:
    """A smoke pass. Not acceptance - the question is only whether the wiring carries."""

    def test_create_and_list_projects(self, app: Any) -> None:
        status, body = call(
            app, "POST", "/projects", body={"name": "Композиция"}, key=_key("proj")
        )
        assert status == 201, body
        assert body["project_uid"].startswith("prj_")

        status, listed = call(app, "GET", "/projects")
        assert status == 200, listed
        assert any(p["project_uid"] == body["project_uid"] for p in listed["items"])

    def test_a_missing_idempotency_key_is_refused_rather_than_generated(
        self, app: Any
    ) -> None:
        """A generated key would make every retry a fresh command, silently."""
        status, body = call(app, "POST", "/projects", body={"name": "NoKey"})
        assert status == 422, body
        assert body["error_code"] == "validation_failed"

    def test_an_unknown_version_is_not_found_rather_than_a_server_fault(
        self, app: Any
    ) -> None:
        """The distinction this suite was written to catch: 404 is wiring that works.

        A 500 here would mean the adapter could not call its module at all, which is
        exactly the defect that survived until the router was first driven.
        """
        status, body = call(app, "GET", "/versions/ver_01ARZ3NDEKTSV4RRFFQ69G5FAV")
        assert status == 404, body
        assert body["error_code"] == "not_found"

    def test_an_unknown_finding_is_not_found(self, app: Any) -> None:
        status, body = call(app, "GET", "/findings/fnd_01ARZ3NDEKTSV4RRFFQ69G5FAV")
        assert status == 404, body

    def test_an_unknown_run_is_not_found(self, app: Any) -> None:
        status, body = call(app, "GET", "/runs/run_01ARZ3NDEKTSV4RRFFQ69G5FAV")
        assert status == 404, body

    def test_an_undeclared_path_is_not_found_and_not_a_crash(self, app: Any) -> None:
        status, _ = call(app, "GET", "/nothing-here")
        assert status == 404


class TestNoOperationAnswersWithAServerFault:
    """The anti-vacuity of this suite: a 500 anywhere means an adapter cannot call out.

    Written as a sweep rather than as six separate assertions so that a thirteenth operation
    added later is covered without anyone remembering to extend a list.
    """

    def test_every_declared_get_answers_without_an_internal_error(self, app: Any) -> None:
        import re

        probes: list[tuple[str, str]] = []
        for route in app.router.routes:
            method = getattr(route, "method", "GET")
            template = getattr(route, "template", getattr(route, "path", ""))
            if method != "GET" or not template:
                continue
            # Fill each path template with a well-formed but absent identity, so the answer
            # is 404 if the wiring carries and 500 if it does not.
            filled = re.sub(r"\{(\w+)\}", lambda m: _absent_identity(m.group(1)), template)
            probes.append((method, filled))

        assert len(probes) >= 5, f"the sweep found too few GET routes: {probes}"
        faults = []
        for method, path in probes:
            status, body = call(app, method, path)
            if status >= 500:
                faults.append((path, status, body))
        assert faults == [], f"operations answered with a server fault: {faults}"


def _absent_identity(parameter: str) -> str:
    prefixes = {
        "project_uid": "prj",
        "version_uid": "ver",
        "run_id": "run",
        "finding_uid": "fnd",
    }
    return f"{prefixes.get(parameter, 'prj')}_01ARZ3NDEKTSV4RRFFQ69G5FAV"


class TestCreateProjectHonoursItsKey:
    """`createProject` requires an Idempotency-Key; until now it discarded one.

    The edge validated the header the frozen document demands and the key stopped there,
    because `B1` published no key-accepting project command. A repeat therefore created a
    second project with a second identity - the exact failure the header exists to prevent.
    `B6` reported it from the router and could not fix it inside its own tree.
    """

    def test_a_repeat_under_one_key_returns_the_same_project(self, app: Any) -> None:
        key = _key("idem")
        first_status, first = call(app, "POST", "/projects", body={"name": "Повтор"}, key=key)
        repeat_status, repeat = call(app, "POST", "/projects", body={"name": "Повтор"}, key=key)
        assert first_status == 201 and repeat_status == 201
        assert first["project_uid"] == repeat["project_uid"], (
            "a repeat under one key created a second project"
        )

    def test_the_same_key_with_a_different_payload_is_a_conflict(self, app: Any) -> None:
        key = _key("idem")
        call(app, "POST", "/projects", body={"name": "Первый"}, key=key)
        status, body = call(app, "POST", "/projects", body={"name": "Второй"}, key=key)
        assert status == 409, body
        assert body["error_code"] == "idempotency_key_reuse"

    def test_two_different_keys_create_two_projects(self, app: Any) -> None:
        """The control. A guard that collapsed every request would look identical."""
        _, one = call(app, "POST", "/projects", body={"name": "A"}, key=_key("idem"))
        _, two = call(app, "POST", "/projects", body={"name": "A"}, key=_key("idem"))
        assert one["project_uid"] != two["project_uid"]
