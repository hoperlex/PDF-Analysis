"""`T-3` -- the operational plane, off the contract and off the authorized surface.

``ALPHA_ROADMAP.md`` section 3 `T-3`: *liveness and readiness answer on a **second port**,
never under ``/api/v1``.* Three consequences, each of them a decision and not an accident:

* **it is a different ASGI application.** Not a route on the API app with the dependency
  excluded, because "excluded from the app-wide dependency" is one edit away from "included
  again", and the failure mode is a health check that starts returning 401 in a deployment.
  `W13-SEAL` section 8.3 names exactly that: *if it inherits an app-wide dependency it stops
  answering and wave 14 discovers that in a deployment.*
* **it is not on the contract document.** The contract declares 106 operations and
  ``web/tests/contract/openapi-drift.contract.test.ts`` counts them; `W13-CONF`'s
  ``test_an_extra_operation_is_caught`` is the case that catches this plane leaking onto the
  API document. ``openapi_url=None`` so this app publishes no document of its own either --
  there is nothing here a client generates code from.
* **readiness does not touch the model provider.** It answers whether this process is wired,
  which is a fact the composition root already settled by constructing: a process that
  started has everything it needs, because ``build_application`` refuses otherwise. Polling a
  paid dependency on every proxy health check would spend money to learn nothing.
* **readiness waits for the API listener** (`D-196`). This plane runs beside the API server
  and does not depend on its socket, so "wired" alone is true tens of milliseconds -- and,
  with a database-touching lifespan, seconds -- before the API port accepts a connection; a
  probe that routes on ``/readyz`` would send traffic to a port that refuses it. The process
  that owns the API server hands this plane a ``serving`` predicate, and ``/readyz`` answers
  ``503`` until it is true -- and again once it turns false because the listener is draining.
  ``/healthz`` never consults it: liveness is "the process answers".

The bodies carry no product meaning, no identity and no version -- an operational plane that
reported the contract version would be a second place the contract version lives.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Final

from fastapi import FastAPI

from auditmanager.api.routers.wire import WireResponse, encode_json, json_response

__all__ = ["LIVENESS_PATH", "READINESS_PATH", "build_health_app"]

LIVENESS_PATH: Final[str] = "/healthz"
READINESS_PATH: Final[str] = "/readyz"


def build_health_app(
    application: Any | None = None,
    *,
    serving: Callable[[], bool] | None = None,
) -> FastAPI:
    """The liveness and readiness plane for one built application.

    ``application`` is the :class:`~auditmanager.bootstrap.composition.Application` this
    process is serving, and is taken only so that readiness can report *something that was
    constructed* rather than a constant. ``None`` is allowed so the plane can be built and
    polled by a test without a database.

    ``serving`` answers "is the API listener bound and still accepting?" -- false before it
    has started and false again once it is shutting down. It is called on every ``/readyz``
    request, so it must be a cheap read of flags the API server owns, and
    an exception from it is a ``500``, never a ready answer. ``None`` means no API listener
    is paired with this plane (a test polling the plane alone), and readiness is then the
    wiring fact alone; the one production caller, ``infra/deploy/serve.py``, passes it, and
    ``tests/integration/composition/test_serve_readiness.py`` fails if it stops.
    """
    app = FastAPI(
        title="auditmanager operational plane",
        openapi_url=None,
        docs_url=None,
        redoc_url=None,
    )

    @app.get(LIVENESS_PATH, include_in_schema=False)
    def liveness() -> WireResponse:
        """The process is running and can answer. Nothing else is claimed."""
        return json_response(200, encode_json({"status": "ok"}))

    @app.get(READINESS_PATH, include_in_schema=False)
    def readiness() -> WireResponse:
        """The process is wired and its API listener is serving.

        See the module note on why this polls nothing else. Before the listener is up the
        answer is ``503`` ``starting``: the process is alive, so ``/healthz`` stays ``200``.
        """
        wired = application is not None
        if serving is not None and not serving():
            return json_response(503, encode_json({"status": "starting", "wired": wired}))
        return json_response(200, encode_json({"status": "ok", "wired": wired}))

    return app
