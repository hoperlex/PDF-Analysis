"""How this suite reaches the twelve operations, after `T-1`.

Before wave 13 these tests called ``dispatch(router, Request.build(...))`` -- two objects
from ``auditmanager.api.routers.http``, which `T-1` retired. What replaces them is a real
ASGI client over a real ``FastAPI`` application built from the same six port adapters the
fixtures already wire, so every assertion in this directory now travels the *actual*
transport: routing, the parameter declarations, the body models, the exception handlers,
the correlation middleware and the body cap.

**The call shape is kept on purpose, and it is worth saying why rather than leaving it to
look like laziness.** These suites assert *which rule refused* -- a constraint name, a
catalog code, a header, an exact message -- and there are several hundred of those
assertions. Re-typing them to a different client's spelling would put every one of them
at risk of being weakened by a transcription slip, in the one wave whose acceptance is
"the surface did not change". So the request and the answer keep the names the assertions
already use, and the thing underneath them is completely new. What changed is the
transport; what did not change is what the suite claims about it, which is the property
the migration had to preserve.

The files that test the *helpers* rather than the surface -- ``test_header_rules.py``,
``test_schema_bounds.py``, ``test_router_and_body_rules.py`` -- are not served by this and
are rewritten instead: ``require_idempotency_key`` is a FastAPI dependency now,
``resolve_correlation_id`` takes a header value instead of a request, ``parse_limit`` and
the three body parsers are gone entirely, and a test that still called them would be
testing nothing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import urlencode

from fastapi import APIRouter, FastAPI
from starlette.testclient import TestClient

from auditmanager.api.app import create_asgi_app
from auditmanager.api.security import API_TOKEN_VARIABLE

__all__ = ["Answer", "Request", "Surface", "TEST_TOKEN", "dispatch", "probe_surface"]

#: The credential this suite configures and presents. A literal, and the only one: a test
#: that read the token out of the application would pass against an application that had
#: stopped checking it.
TEST_TOKEN = "w13-api-suite-token"


@dataclass(frozen=True, slots=True)
class Request:
    """One inbound request, in the vocabulary this suite already speaks."""

    method: str
    path: str
    headers: Mapping[str, str] = field(default_factory=dict)
    query: Mapping[str, Sequence[str]] = field(default_factory=dict)
    body: bytes = b""

    @classmethod
    def build(
        cls,
        method: str,
        target: str,
        *,
        headers: Mapping[str, str] | Iterable[tuple[str, str]] = (),
        body: bytes = b"",
    ) -> "Request":
        path, _, query = target.partition("?")
        return cls(
            method=method.upper(),
            path=path if not query else f"{path}?{query}",
            headers=dict(headers),
            body=body,
        )

    @property
    def target(self) -> str:
        if not self.query:
            return self.path
        pairs = [
            (name, value)
            for name, values in self.query.items()
            for value in (values if isinstance(values, (list, tuple)) else [values])
        ]
        return f"{self.path}?{urlencode(pairs)}" if pairs else self.path


@dataclass(frozen=True, slots=True)
class Answer:
    """One outbound response, exactly as the application emitted it.

    ``headers`` comes from ``httpx``'s ``raw``, not from the case-folding mapping, so a
    test may assert the header's name as the contract spells it.
    """

    status: int
    headers: tuple[tuple[str, str], ...]
    body: bytes

    def header(self, name: str) -> str | None:
        lowered = name.lower()
        for key, value in self.headers:
            if key.lower() == lowered:
                return value
        return None

    def json(self) -> Any:
        return json.loads(self.body)


class Surface:
    """An ``APIRouter`` of the twelve operations, and the application that serves it.

    The application is built once per surface and cached: assembling a ``FastAPI`` builds
    the whole dependency graph, and doing that per request would make this suite several
    minutes slower for no additional evidence.
    """

    __slots__ = ("router", "_client", "_app")

    def __init__(self, router: APIRouter) -> None:
        self.router = router
        self._app: FastAPI | None = None
        self._client: TestClient | None = None

    @property
    def app(self) -> FastAPI:
        if self._app is None:
            self._app = create_asgi_app(
                environ={API_TOKEN_VARIABLE: TEST_TOKEN},
                application=_PreBuilt(self.router),  # type: ignore[arg-type]
            )
        return self._app

    @property
    def client(self) -> TestClient:
        if self._client is None:
            self._client = TestClient(self.app, raise_server_exceptions=False)
        return self._client

    # --- the twelve operations, as declarations rather than as answers -----------------

    @property
    def routes(self) -> tuple[Any, ...]:
        """Only the twelve. ``APIRouter.routes`` carries nothing else here, but the filter
        is explicit so that a future default route could not quietly become a thirteenth."""
        return tuple(
            route for route in self.router.routes if getattr(route, "operation_id", None)
        )

    def match(self, request: "Request") -> tuple[Any, Mapping[str, str]]:
        """The route that would serve ``request``, and the path parameters it binds.

        Starlette's own matcher, asked directly. ``Router.match`` used to be this suite's
        way of proving a path template is *reachable* -- that no placeholder swallows a
        slash and no template has a typo -- and that question still has to be asked of the
        real router rather than inferred from a 404, because a 404 cannot tell "no such
        route" from "that route refused you".
        """
        from starlette.routing import Match

        scope = {
            "type": "http",
            "method": request.method.upper(),
            "path": request.path.partition("?")[0],
            "path_params": {},
            "headers": [],
            "query_string": b"",
            "root_path": "",
        }
        for route in self.routes:
            verdict, child = route.matches(scope)
            if verdict is Match.FULL:
                return route, child.get("path_params", {})
        raise LookupError(f"no route matches {request.method} {request.path}")

    @property
    def operation_ids(self) -> frozenset[str]:
        return frozenset(route.operation_id for route in self.routes)

    def signature(self) -> frozenset[tuple[str, str, str]]:
        """``(operationId, METHOD, path)`` for every operation.

        The value the twelve-operation assertions compare against the frozen document.
        One ``APIRoute`` carries a set of methods; each pair is one row here, so an
        operation that quietly gained a second method changes the set.
        """
        return frozenset(
            (route.operation_id, method, route.path)
            for route in self.routes
            for method in sorted(route.methods)
        )

    def send(
        self,
        method: str,
        target: str,
        *,
        headers: Mapping[str, str] = {},
        body: bytes = b"",
        credential: str | None = TEST_TOKEN,
    ) -> Answer:
        """Drive one request. ``credential=None`` presents none, for the seam's own tests."""
        sent = dict(headers)
        if credential is not None and not any(
            name.lower() == "authorization" for name in sent
        ):
            sent["Authorization"] = f"Bearer {credential}"
        response = self.client.request(method, target, headers=sent, content=body)
        return Answer(
            status=response.status_code,
            headers=tuple(
                (name.decode("latin-1"), value.decode("latin-1"))
                for name, value in response.headers.raw
            ),
            body=response.content,
        )


class _PreBuilt:
    """Just enough of ``Application`` for ``create_asgi_app`` to take a router as given.

    ``create_asgi_app(application=...)`` reads two attributes since `D-20`: the router, and
    the carrier it publishes as ``app.state.run_carrier``. Standing in for the whole
    composition root here is what lets this suite keep wiring the seam adapters it has
    always wired -- three of the shapes the frozen document requires still have no producer
    outside it -- without a database-backed application being built per test.

    The carrier is an :class:`~auditmanager.runs.InlineCarrier` and nothing in this suite
    submits to it: the seam adapters answer from rows this suite writes itself and start no
    run. It is a real carrier rather than ``None`` so that a test which *did* start one
    would get a finished run rather than an ``AttributeError`` three frames away from the
    cause. ``session_factory`` is deliberately absent: it is read only by the startup
    lifespan, and this driver builds its ``TestClient`` without entering one.
    """

    __slots__ = ("router", "carrier")

    def __init__(self, router: APIRouter) -> None:
        from auditmanager.runs import InlineCarrier

        self.router = router
        self.carrier = InlineCarrier()


def dispatch(
    surface: Surface,
    request: Request,
    *,
    credential: str | None = TEST_TOKEN,
) -> Answer:
    """Resolve one request through the real application."""
    return surface.send(
        request.method,
        request.target,
        headers=request.headers,
        body=request.body,
        credential=credential,
    )


def probe_surface(handler: Any) -> Surface:
    """A one-operation surface whose handler is ``handler``, on the real middleware stack.

    Several tests in this suite need to watch what the edge does with a handler that
    *fails* -- a ``DBAPIError`` carrying one of the three custom SQLSTATEs, a plain
    ``RuntimeError`` with a filesystem path in its message. Before `T-1` they built a
    two-line ``Router`` around a callable. The replacement builds a real ``FastAPI``
    application around one, through :func:`~auditmanager.api.app.create_asgi_app`, so the
    answer travels the same correlation middleware, the same
    ``FailureEnvelopeMiddleware`` and the same exception handlers as the twelve.

    That is strictly more evidence than the old probe gave: the old one exercised
    ``dispatch``'s own try/except, which is gone, and this one exercises the path a real
    failure now takes.
    """
    router = APIRouter()

    @router.get("/probe", operation_id="probe", tags=["probe"])
    def probe() -> Any:
        return handler()

    return Surface(router)
