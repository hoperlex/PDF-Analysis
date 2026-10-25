"""`D-196`: ``/readyz`` is not ready until the API listener is serving, ``/healthz`` never waits.

The health plane runs beside the API server and does not depend on its socket, so before this
repair it answered ``200`` for as long as the API's start-up took (19 to 26 ms measured in
`GATE-REPAIR-01`, longer when the lifespan touches the database) while the API port refused
connections. ``build_health_app`` now takes the flag the API server owns. These cases drive the
plane with an injected flag; they open no socket. That ``infra/deploy/serve.py`` really hands
the plane the API server's own flag is ``tests/integration/composition/test_serve_readiness.py``.
"""

from __future__ import annotations

import json

from starlette.testclient import TestClient

from auditmanager.api.health import LIVENESS_PATH, READINESS_PATH, build_health_app


class _Flag:
    """The shape of ``uvicorn.Server.started``: false until the listener is up, then true."""

    def __init__(self) -> None:
        self.up = False

    def __call__(self) -> bool:
        return self.up


def _body(response) -> dict:  # type: ignore[no-untyped-def]
    return json.loads(response.content)


def test_readiness_is_refused_while_the_listener_is_not_serving() -> None:
    flag = _Flag()
    client = TestClient(build_health_app(object(), serving=flag))

    response = client.get(READINESS_PATH)

    assert response.status_code == 503, response.content
    assert _body(response) == {"status": "starting", "wired": True}


def test_readiness_turns_on_when_the_flag_does_and_keeps_its_old_body() -> None:
    flag = _Flag()
    client = TestClient(build_health_app(object(), serving=flag))
    assert client.get(READINESS_PATH).status_code == 503

    flag.up = True
    response = client.get(READINESS_PATH)

    assert response.status_code == 200, response.content
    # Byte for byte what the plane answered before the flag existed.
    assert response.content == b'{"status": "ok", "wired": true}'


def test_liveness_never_consults_the_flag() -> None:
    """A process that is up but not yet serving is alive: the container healthcheck reads this."""
    calls: list[str] = []

    def serving() -> bool:
        calls.append("consulted")
        return False

    client = TestClient(build_health_app(object(), serving=serving))
    response = client.get(LIVENESS_PATH)

    assert response.status_code == 200, response.content
    assert _body(response) == {"status": "ok"}
    assert calls == []


def test_an_unwired_plane_that_is_serving_still_reports_unwired() -> None:
    """The flag adds a condition; it does not replace the wiring fact."""
    client = TestClient(build_health_app(None, serving=lambda: True))

    response = client.get(READINESS_PATH)

    assert response.status_code == 200
    assert _body(response) == {"status": "ok", "wired": False}


def test_a_failing_flag_is_an_error_and_never_a_ready_answer() -> None:
    def serving() -> bool:
        raise RuntimeError("the listener state could not be read")

    client = TestClient(build_health_app(object(), serving=serving), raise_server_exceptions=False)

    assert client.get(READINESS_PATH).status_code == 500
