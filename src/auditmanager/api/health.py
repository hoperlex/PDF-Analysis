"""`T-3` -- the operational plane, off the contract and off the authorized surface.

``ALPHA_ROADMAP.md`` section 3 `T-3`: *liveness and readiness answer on a **second port**,
never under ``/api/v1``.* Three consequences, each of them a decision and not an accident:

* **it is a different ASGI application.** Not a route on the API app with the dependency
  excluded, because "excluded from the app-wide dependency" is one edit away from "included
  again", and the failure mode is a health check that starts returning 401 in a deployment.
  `W13-SEAL` section 8.3 names exactly that: *if it inherits an app-wide dependency it stops
  answering and wave 14 discovers that in a deployment.*
* **it is not on the contract document.** The contract declares fifteen operations and
  ``web/tests/contract/openapi-drift.contract.test.ts`` counts them; `W13-CONF`'s
  ``test_an_extra_operation_is_caught`` is the case that catches this plane leaking onto the
  API document. ``openapi_url=None`` so this app publishes no document of its own either --
  there is nothing here a client generates code from.
* **readiness does not touch the model provider.** It answers whether this process is wired,
  which is a fact the composition root already settled by constructing: a process that
  started has everything it needs, because ``build_application`` refuses otherwise. Polling a
  paid dependency on every proxy health check would spend money to learn nothing.

The bodies carry no product meaning, no identity and no version -- an operational plane that
reported the contract version would be a second place the contract version lives.
"""

from __future__ import annotations

from typing import Any, Final

from fastapi import FastAPI

from auditmanager.api.routers.wire import WireResponse, encode_json, json_response

__all__ = ["LIVENESS_PATH", "READINESS_PATH", "build_health_app"]

LIVENESS_PATH: Final[str] = "/healthz"
READINESS_PATH: Final[str] = "/readyz"


def build_health_app(application: Any | None = None) -> FastAPI:
    """The liveness and readiness plane for one built application.

    ``application`` is the :class:`~auditmanager.bootstrap.composition.Application` this
    process is serving, and is taken only so that readiness can report *something that was
    constructed* rather than a constant. ``None`` is allowed so the plane can be built and
    polled by a test without a database.
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
        """The process is wired. See the module note on why this polls nothing."""
        return json_response(
            200, encode_json({"status": "ok", "wired": application is not None})
        )

    return app
