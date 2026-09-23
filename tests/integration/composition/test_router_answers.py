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

from starlette.testclient import TestClient

from auditmanager.api.app import create_app, create_asgi_app
from auditmanager.api.routers.idempotency import IDEMPOTENCY_HEADER
from auditmanager.api.security import API_TOKEN_VARIABLE

#: `T-6`. This suite configures the seam's deployment secret, as a literal, and presents
#: a credential minted from it -- which is what the deployment itself does.
DEPLOYMENT_SECRET = "composition-static-token"

_STATIC_TOKEN_CACHE: str | None = None


def static_token() -> str:
    """A credential this lane's API accepts, for an account this lane really has.

    **Lazy and memoised on purpose.** It opens a database connection, and doing that at
    import time would turn a lane whose services are not up into a *collection* error --
    which reads as a broken suite rather than as an absent lane.

    `W39-REVOKE`: a credential is refused unless the account it names exists and still
    accepts that credential's generation, so this suite's old habit of minting for an
    identity it invented is now presenting something the seam is correct to reject. The row
    is written, the epoch is read back out of it, and the credential is minted from what the
    database says. See ``tests/support/accounts.py``.
    """
    global _STATIC_TOKEN_CACHE
    if _STATIC_TOKEN_CACHE is None:
        from am_test_accounts import provisioned_credential

        _STATIC_TOKEN_CACHE = provisioned_credential(DEPLOYMENT_SECRET, "composition-suite")
    return _STATIC_TOKEN_CACHE



class Composed:
    """The built application, and an ASGI client over the application that serves it."""

    __slots__ = ("application", "client")

    def __init__(self, application: Any, client: TestClient) -> None:
        self.application = application
        self.client = client

    @property
    def router(self) -> Any:
        return self.application.router


@pytest.fixture(scope="module")
def app() -> Composed:
    assert os.environ.get("DATABASE_URL"), "this suite needs the lane's .env loaded"
    environ = dict(os.environ) | {API_TOKEN_VARIABLE: DEPLOYMENT_SECRET}
    application = create_app(environ=environ)
    asgi = create_asgi_app(environ=environ, application=application)
    return Composed(application, TestClient(asgi, raise_server_exceptions=False))


def _key(label: str) -> str:
    return f"{label}-{uuid.uuid4().hex[:16]}"


def call(
    app: Composed,
    method: str,
    path: str,
    *,
    body: Any = None,
    key: str | None = None,
    query: dict[str, list[str]] | None = None,
) -> tuple[int, Any]:
    """One request over the real transport.

    Re-pointed by `W13-API`: ``Request.build`` plus ``dispatch`` became a
    ``starlette.testclient.TestClient`` over ``create_asgi_app()``. This suite asks one
    question -- does the wiring carry from the edge to the module and back -- and that
    question is now asked of the application that actually serves, middlewares and all.
    """
    from urllib.parse import urlencode

    headers: dict[str, str] = {"Authorization": f"Bearer {static_token()}"}
    payload = b""
    if body is not None:
        headers["content-type"] = "application/json"
        payload = json.dumps(body).encode()
    if key is not None:
        headers[IDEMPOTENCY_HEADER] = key
    target = path
    if query:
        pairs = [(name, value) for name, values in query.items() for value in values]
        target = f"{path}?{urlencode(pairs)}"
    response = app.client.request(method, target, headers=headers, content=payload)
    decoded: Any
    try:
        decoded = json.loads(response.content) if response.content else None
    except ValueError:
        decoded = response.content
    return response.status_code, decoded


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
            template = getattr(route, "path", "")
            if "GET" not in getattr(route, "methods", ()) or not template:
                continue
            method = "GET"
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


class TestTheAdaptersHonourWhatThePortsDeclare:
    """A declared parameter that an adapter swallows is worse than one that is refused.

    The router read `category` and `verdict`, validated them against their enums and passed
    them; the adapter took `**_` and dropped both, so a filtered request returned everything
    and looked like it had worked. This checks the shape rather than the behaviour, because
    the behaviour needs a populated run and the shape is what silently drifted.
    """

    def test_every_adapter_accepts_every_parameter_its_port_declares(self) -> None:
        import inspect

        from auditmanager.api.routers import ports as port_module
        from auditmanager.bootstrap import adapters as adapter_module

        pairs = [
            ("ProjectPort", "ProjectAdapter"),
            ("DocumentPort", "DocumentAdapter"),
            ("RunPort", "RunAdapter"),
            ("FindingPort", "FindingAdapter"),
            ("DecisionPort", "DecisionAdapter"),
            ("CsvExportPort", "CsvExportAdapter"),
        ]
        assert len(pairs) == 6, "the six ports build_router takes"

        problems: list[str] = []
        for port_name, adapter_name in pairs:
            port = getattr(port_module, port_name)
            adapter = getattr(adapter_module, adapter_name)
            for method_name in dir(port):
                if method_name.startswith("_"):
                    continue
                port_method = getattr(port, method_name, None)
                adapter_method = getattr(adapter, method_name, None)
                if not callable(port_method) or adapter_method is None:
                    continue
                declared = {
                    name
                    for name, p in inspect.signature(port_method).parameters.items()
                    if name != "self" and p.kind is not p.VAR_KEYWORD
                }
                signature = inspect.signature(adapter_method)
                accepted = {n for n in signature.parameters if n != "self"}
                swallows = any(
                    p.kind is p.VAR_KEYWORD for p in signature.parameters.values()
                )
                missing = declared - accepted
                if missing:
                    where = "swallowed by **kwargs" if swallows else "absent"
                    problems.append(
                        f"{adapter_name}.{method_name}: {sorted(missing)} {where}"
                    )
        assert problems == [], (
            "an adapter does not accept a parameter its port declares, so the value is "
            f"dropped between the router and the module: {problems}"
        )


class TestAFailedStageReportsItsCode:
    """A stage that failed must say why, through the API, in the catalog's vocabulary.

    The gap this closes is narrow and was expensive: a `dependency_unavailable` failure -
    **retryable** - was published with `error_code: null`, so the API reported a transport
    outage as an unclassified analysis failure and an operator would not retry a run that
    failed only because the provider was down.

    It survived a repair that named it correctly. The fix read `stage.error["error_code"]`
    while the stored key is `code`, and nothing noticed because no test drove a failed stage
    through the router - the same blind spot that hid four defects in this same method.
    """

    def test_the_adapter_reads_the_key_the_engine_writes(self) -> None:
        """Pins the two halves together so a rename on either side fails here.

        Asserted against the engine's own type rather than a literal, because a test that
        restates the key is the mechanism that let the mismatch survive.
        """
        import dataclasses as dc

        from auditmanager.analysis.engine.result import StageError

        stored = {field.name for field in dc.fields(StageError)}
        assert "code" in stored, "the engine no longer stores `code`; the adapter must follow"

        import inspect

        from auditmanager.bootstrap import adapters

        source = inspect.getsource(adapters._run_status_view)
        assert '.get("code")' in source, (
            "the adapter does not read the key the engine writes, so a failed stage "
            "publishes a null error_code"
        )
        assert '.get("error_code")' not in source, (
            "the adapter still reads `error_code`, which the engine does not store"
        )

    def test_a_stored_failure_renders_its_catalog_code(self, app: Any) -> None:
        """Drives the mapping over a real stored error rather than a constructed one."""
        import os

        from sqlalchemy import create_engine, text

        engine = create_engine(os.environ["DATABASE_URL"])
        with engine.connect() as connection:
            row = connection.execute(
                text(
                    "SELECT run_id FROM stage_result WHERE error IS NOT NULL "
                    "AND error ? 'code' LIMIT 1"
                )
            ).first()
        if row is None:
            pytest.skip("this database holds no failed stage to render")

        status, body = call(app, "GET", f"/runs/{row[0]}")
        assert status == 200, body
        failed = [s for s in body["stages"] if s["status"] != "succeeded"]
        assert failed, "the run has no non-succeeded stage to check"
        assert all(s.get("error_code") for s in failed), (
            f"a failed stage published no error_code: {failed}"
        )
