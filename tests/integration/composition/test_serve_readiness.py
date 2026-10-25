"""`D-196`: ``infra/deploy/serve.py`` makes ``/readyz`` wait for the API server it starts.

``tests/unit/api/test_readiness_waits_for_the_listener.py`` shows the health plane honours an
injected flag. What only ``serve.py`` can show is that the flag it injects is the *API
server's own* ``started``, on the one server it then runs -- not a constant, not the health
server's. ``uvicorn`` is replaced here by a recording stand-in, so the process binds nothing
and the case needs no database and no port; the real-socket counterpart is the QA harness's
start-up in ``tests/integration/qa_w55b/qa_support.py`` (a database lane), which still waits
for both planes and now has the service on its side.

``GATE-REPAIR-01`` measured the window this closes: 19 to 26 ms of ``/readyz`` ``200`` before
the API port was bound, over 12 real starts.
"""

from __future__ import annotations

import importlib.util
import threading
import types
from pathlib import Path
from typing import Any

from starlette.testclient import TestClient

ROOT = Path(__file__).resolve().parents[3]
SERVE = ROOT / "infra/deploy/serve.py"

API_APP = object()


def _load_serve() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("serve_under_test", SERVE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Config:
    def __init__(self, app: Any, **options: Any) -> None:
        self.app = app
        self.options = options


def _run_main(monkeypatch: Any, on_api_run: Any) -> tuple[Any, Any]:
    """Run ``serve.main`` against stand-in servers; return (health app, api server).

    ``on_api_run(server, health_app)`` is called where ``uvicorn.Server.run`` would block.
    """
    serve = _load_serve()
    servers: list[Any] = []
    health_ran = threading.Event()

    class _Server:
        def __init__(self, config: _Config) -> None:
            self.config = config
            self.started = False
            servers.append(self)

        def run(self) -> None:
            if self.config.app is API_APP:
                assert health_ran.wait(5), "the health plane was not started before the API blocked"
                health = next(s for s in servers if s.config.app is not API_APP)
                on_api_run(self, health.config.app)
            else:
                health_ran.set()

    application = types.SimpleNamespace(
        settings=types.SimpleNamespace(provider_mode="recorded"),
        router=types.SimpleNamespace(routes=[]),
    )
    monkeypatch.setattr(serve, "create_app", lambda environ: application)
    monkeypatch.setattr(serve, "create_asgi_app", lambda environ=None, application=None: API_APP)
    monkeypatch.setattr(serve, "uvicorn", types.SimpleNamespace(Config=_Config, Server=_Server))
    monkeypatch.setenv("AUDITMANAGER_API_PORT", "28990")
    monkeypatch.setenv("AUDITMANAGER_HEALTH_PORT", "28991")

    assert serve.main() == 0
    api = next(s for s in servers if s.config.app is API_APP)
    health = next(s for s in servers if s.config.app is not API_APP)
    assert len(servers) == 2
    return health.config.app, api


def test_readyz_is_refused_until_the_api_server_the_process_runs_has_started(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    observed: dict[str, int] = {}

    def on_api_run(server: Any, health_app: Any) -> None:
        client = TestClient(health_app)
        observed["live before bind"] = client.get("/healthz").status_code
        observed["ready before bind"] = client.get("/readyz").status_code
        server.started = True  # what uvicorn does once the lifespan is up and the socket bound
        observed["ready after bind"] = client.get("/readyz").status_code

    _run_main(monkeypatch, on_api_run)

    assert observed == {
        "live before bind": 200,
        "ready before bind": 503,
        "ready after bind": 200,
    }


def test_the_health_plane_is_built_for_the_application_the_process_wired(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Readiness keeps reporting ``wired`` for the real application, not for ``None``."""
    seen: dict[str, Any] = {}

    def on_api_run(server: Any, health_app: Any) -> None:
        server.started = True
        seen["body"] = TestClient(health_app).get("/readyz").json()

    _run_main(monkeypatch, on_api_run)

    assert seen["body"] == {"status": "ok", "wired": True}
