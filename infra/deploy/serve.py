"""The alpha's process entry point: one built application, served on two ports.

`W13-API` built everything this needs and serves none of it. ``api/app.py`` has
:func:`create_asgi_app` (the sixteen operations) and ``api/health.py`` has
:func:`build_health_app` (`T-3`'s liveness and readiness), and ``api/app.py:main`` only
*constructs* and prints -- deliberately, so an operator can ask "would this process
start?" for free. Nothing in the repository binds either application to a socket. This
module is that binding, and it lives in ``infra/`` because it is packaging, not product:
`W14-PKG` owns ``infra/**`` and does not touch ``src/auditmanager/api/**``.

**Why one process and not two containers.** ``health.py``'s readiness reports *whether
this process is wired*, which is a fact the composition root settles by constructing. A
second container answering readiness would report on its own wiring and tell the proxy
nothing about the process actually serving ``/api/v1``. So the application is built once,
here, and both ASGI apps are handed the same object.

**Why a thread and not two coroutines.** ``uvicorn.Server.serve`` installs signal handlers
only on the main thread, so the health server runs as a daemon thread with signal handling
skipped and the API server keeps the main thread and the SIGTERM that stops the container.
A daemon thread also cannot outlive a crashed API server and leave a container that still
answers ``/healthz`` while serving nothing.

**Configuration is the environment and nothing else.** ``create_asgi_app(environ=None)``
reads ``os.environ``; ``bootstrap/settings.py:load`` refuses to start on a missing value,
``AUDITMANAGER_API_TOKEN`` among them since `W14-PKG`. So a container with an incomplete
environment exits non-zero at start instead of serving refusals.
"""

from __future__ import annotations

import os
import sys
import threading
from typing import Final

import uvicorn

from auditmanager.api.app import create_app, create_asgi_app
from auditmanager.api.composition import ConfigurationError
from auditmanager.api.health import build_health_app

#: The two ports, and the interface. Defaults are the container's own, not a host's: the
#: compose file publishes them and the proxy is the only thing that reaches the API.
API_PORT_VARIABLE: Final[str] = "AUDITMANAGER_API_PORT"
HEALTH_PORT_VARIABLE: Final[str] = "AUDITMANAGER_HEALTH_PORT"
BIND_VARIABLE: Final[str] = "AUDITMANAGER_BIND_HOST"

DEFAULT_API_PORT: Final[int] = 8000
DEFAULT_HEALTH_PORT: Final[int] = 8001
DEFAULT_BIND_HOST: Final[str] = "0.0.0.0"  # noqa: S104 - inside a container network


def _port(name: str, default: int, environ: dict[str, str]) -> int:
    raw = environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ConfigurationError(
            f"{name} is {raw!r}, which is not a port number"
        ) from None
    if not 1 <= value <= 65535:
        raise ConfigurationError(f"{name} is {value}, outside 1-65535")
    return value


def main(argv: list[str] | None = None) -> int:
    """Build once, serve twice. Returns non-zero without binding anything on refusal."""
    del argv
    environ = dict(os.environ)
    try:
        api_port = _port(API_PORT_VARIABLE, DEFAULT_API_PORT, environ)
        health_port = _port(HEALTH_PORT_VARIABLE, DEFAULT_HEALTH_PORT, environ)
        if api_port == health_port:
            raise ConfigurationError(
                f"{API_PORT_VARIABLE} and {HEALTH_PORT_VARIABLE} are both {api_port}; "
                "`T-3` puts the operational plane on a second port and one socket cannot "
                "be two"
            )
        application = create_app(environ)
    except ConfigurationError as failure:
        print(f"auditmanager: refusing to start: {failure}", file=sys.stderr)
        return 2

    bind_host = environ.get(BIND_VARIABLE, "").strip() or DEFAULT_BIND_HOST
    api_app = create_asgi_app(environ=environ, application=application)
    health_app = build_health_app(application)

    health = uvicorn.Server(
        uvicorn.Config(health_app, host=bind_host, port=health_port, access_log=False)
    )
    threading.Thread(target=health.run, name="health-plane", daemon=True).start()

    print(
        f"auditmanager: wired, provider_mode={application.settings.provider_mode}, "
        f"operations={len(application.router.routes)}, "
        f"api={bind_host}:{api_port}, health={bind_host}:{health_port}",
        flush=True,
    )
    uvicorn.Server(
        uvicorn.Config(api_app, host=bind_host, port=api_port, access_log=True)
    ).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
