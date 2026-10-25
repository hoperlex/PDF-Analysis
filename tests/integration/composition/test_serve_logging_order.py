"""``DEBT-READYZ-ERRORS-FIX-01``: the API ``Config`` is built after the health plane's.

``uvicorn.Config.__init__`` runs ``configure_logging``. With ``access_log=True`` it applies the
dict config that attaches a handler to the *process-global* ``uvicorn.access`` logger; with
``access_log=False`` it empties that logger's handlers. So the last ``Config`` built decides
whether the process has an access log at all. ``serve.main`` builds the health plane's
(``access_log=False``) first and the API's (``access_log=True``) last; the first cut of
``D-196`` built them the other way round and silenced the API's access log (a ``GET`` answered
``200`` and logged nothing).

``test_serve_readiness.py`` replaces ``uvicorn.Config`` with a fake, which cannot see this.
These cases use the *real* ``uvicorn.Config`` and replace only ``uvicorn.Server``, so nothing
binds a port and the case needs no database. The global logger state is snapshotted and put back.
"""

from __future__ import annotations

import importlib.util
import logging
import types
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import uvicorn

ROOT = Path(__file__).resolve().parents[3]
SERVE = ROOT / "infra/deploy/serve.py"

API_APP = object()

_LOGGERS = ("uvicorn", "uvicorn.error", "uvicorn.access")


def _load_serve() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("serve_logging_order_under_test", SERVE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def isolated_uvicorn_loggers() -> Iterator[logging.Logger]:
    """Start from an empty access logger and put every uvicorn logger back afterwards."""
    saved = {
        name: (
            list(logging.getLogger(name).handlers),
            logging.getLogger(name).level,
            logging.getLogger(name).propagate,
            logging.getLogger(name).disabled,
        )
        for name in _LOGGERS
    }
    access = logging.getLogger("uvicorn.access")
    access.handlers = []  # a handler left by an earlier test must not make a pass vacuous
    try:
        yield access
    finally:
        for name, (handlers, level, propagate, disabled) in saved.items():
            logger = logging.getLogger(name)
            logger.handlers = handlers
            logger.setLevel(level)
            logger.propagate = propagate
            logger.disabled = disabled


def _run_main_with_real_configs(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Run ``serve.main`` with real ``uvicorn.Config`` and stand-in servers.

    Returns the order the two configs were built in: ``"health"`` and ``"api"``.
    """
    serve = _load_serve()
    built: list[str] = []

    def real_config(app: Any, **options: Any) -> uvicorn.Config:
        built.append("api" if app is API_APP else "health")
        return uvicorn.Config(app, **options)

    class _Server:
        def __init__(self, config: uvicorn.Config) -> None:
            self.config = config
            self.started = False
            self.should_exit = False
            self.force_exit = False

        def run(self) -> None:
            return None

    application = types.SimpleNamespace(
        settings=types.SimpleNamespace(provider_mode="recorded"),
        router=types.SimpleNamespace(routes=[]),
    )
    monkeypatch.setattr(serve, "create_app", lambda environ: application)
    monkeypatch.setattr(serve, "create_asgi_app", lambda environ=None, application=None: API_APP)
    monkeypatch.setattr(serve, "uvicorn", types.SimpleNamespace(Config=real_config, Server=_Server))
    monkeypatch.setenv("AUDITMANAGER_API_PORT", "28994")
    monkeypatch.setenv("AUDITMANAGER_HEALTH_PORT", "28995")

    assert serve.main() == 0
    return built


def test_the_api_access_log_survives_the_health_plane_config(
    monkeypatch: pytest.MonkeyPatch, isolated_uvicorn_loggers: logging.Logger
) -> None:
    built = _run_main_with_real_configs(monkeypatch)

    access = isolated_uvicorn_loggers
    assert access.handlers, (
        "the process has no access-log handler after serve.main built its configs "
        f"(built in the order {built}); the API's access_log=True was overridden"
    )
    assert access.propagate is False


def test_the_api_config_is_built_after_the_health_plane_config(
    monkeypatch: pytest.MonkeyPatch, isolated_uvicorn_loggers: logging.Logger
) -> None:
    """The cause behind the effect above, so a failure names the reordering."""
    built = _run_main_with_real_configs(monkeypatch)

    assert built == ["health", "api"]


def test_premise_the_config_built_last_decides_the_access_log(
    isolated_uvicorn_loggers: logging.Logger,
) -> None:
    """The guards above are only worth anything while uvicorn behaves like this; say so out loud."""
    access = isolated_uvicorn_loggers

    uvicorn.Config(object(), access_log=True)
    assert access.handlers, "an access_log=True config attaches the access handler"

    uvicorn.Config(object(), access_log=False)
    assert access.handlers == [], "a later access_log=False config strips it again"
    assert access.propagate is False

    uvicorn.Config(object(), access_log=True)
    assert access.handlers, "and a later access_log=True config puts it back"
