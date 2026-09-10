"""The transport primitives the routers are written against.

There is deliberately **no HTTP framework here**. ``docs/program/P02_LOCK.json`` pins
three runtime distributions -- ``pdfplumber``, ``pypdf`` and ``anthropic`` -- and none
of them is a web framework. A Gate B session may not add a root dependency, so this
module supplies the three things a router actually needs, in about a hundred lines:

* :class:`Request` -- method, path, case-insensitive headers, parsed query, raw body;
* :class:`Response` -- status, header pairs, raw body;
* :class:`Route` / :class:`Router` -- an operation-id keyed table with ``{name}``
  path-template matching.

Everything here is a value. Nothing opens a socket, reads an environment variable or
constructs a dependency: binding this table to a server is the composition root's job
(``api/app.py``, owned by the integrator in Gate C), and a router that reached for a
socket would have taken that decision away from it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Final, Iterable, Iterator, Mapping, Sequence
from urllib.parse import parse_qs

__all__ = [
    "Handler",
    "Headers",
    "MethodNotAllowed",
    "NoRoute",
    "Request",
    "Response",
    "Route",
    "Router",
    "json_response",
]

#: A ``{name}`` placeholder in an OpenAPI path template.
_PLACEHOLDER: Final[re.Pattern[str]] = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


class Headers(Mapping[str, str]):
    """Case-insensitive, last-value-wins header mapping.

    HTTP header names are case-insensitive, so a router that reads ``Idempotency-Key``
    must also see ``idempotency-key``. Getting that wrong makes a required-header
    contract depend on the client's capitalisation, which is exactly the class of
    defect this type removes.
    """

    __slots__ = ("_values",)

    def __init__(self, values: Mapping[str, str] | Iterable[tuple[str, str]] = ()) -> None:
        items = values.items() if isinstance(values, Mapping) else values
        self._values: dict[str, str] = {str(k).lower(): str(v) for k, v in items}

    def __getitem__(self, key: str) -> str:
        return self._values[key.lower()]

    def __iter__(self) -> Iterator[str]:
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        return f"Headers({self._values!r})"


@dataclass(frozen=True, slots=True)
class Request:
    """One inbound request, already decoded off the wire."""

    method: str
    path: str
    headers: Headers = field(default_factory=Headers)
    query: Mapping[str, Sequence[str]] = field(default_factory=dict)
    body: bytes = b""
    #: Filled in by :meth:`Router.match`; a handler reads its path parameters here.
    path_params: Mapping[str, str] = field(default_factory=dict)

    @classmethod
    def build(
        cls,
        method: str,
        target: str,
        *,
        headers: Mapping[str, str] | Iterable[tuple[str, str]] = (),
        body: bytes = b"",
    ) -> "Request":
        """Build a request from a raw request target, splitting off the query string."""
        path, _, query_string = target.partition("?")
        return cls(
            method=method.upper(),
            path=path,
            headers=Headers(headers),
            query=parse_qs(query_string, keep_blank_values=True),
            body=body,
        )

    def query_one(self, name: str) -> str | None:
        """The single value of a query parameter, or ``None`` when it is absent.

        A repeated parameter takes its last value rather than silently taking the
        first: a client that sent ``?limit=1&limit=200`` gets the value it wrote last.
        """
        values = self.query.get(name)
        if not values:
            return None
        return values[-1]

    def with_path_params(self, params: Mapping[str, str]) -> "Request":
        return Request(
            method=self.method,
            path=self.path,
            headers=self.headers,
            query=self.query,
            body=self.body,
            path_params=dict(params),
        )


@dataclass(frozen=True, slots=True)
class Response:
    """One outbound response. ``headers`` is a sequence of pairs, so a header may repeat."""

    status: int
    headers: tuple[tuple[str, str], ...] = ()
    body: bytes = b""

    def with_header(self, name: str, value: str) -> "Response":
        """Return a copy carrying one more header. Never mutates."""
        return Response(self.status, self.headers + ((name, value),), self.body)

    def header(self, name: str) -> str | None:
        lowered = name.lower()
        for key, value in self.headers:
            if key.lower() == lowered:
                return value
        return None


def json_response(status: int, payload: bytes) -> Response:
    return Response(
        status,
        (
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(payload))),
        ),
        payload,
    )


Handler = Callable[[Request], Response]


@dataclass(frozen=True, slots=True)
class Route:
    """One frozen operation, bound to the callable that serves it.

    ``operation_id`` is the identity: ``tests/integration/api`` asserts the router's
    operation-id set against ``contracts/api/v1/openapi.json`` rather than against a
    list written out by hand, so a thirteenth operation cannot be added quietly and a
    missing one cannot be overlooked.
    """

    operation_id: str
    method: str
    template: str
    handler: Handler

    @property
    def pattern(self) -> re.Pattern[str]:
        return _compile(self.template)


_PATTERNS: dict[str, re.Pattern[str]] = {}


def _compile(template: str) -> re.Pattern[str]:
    cached = _PATTERNS.get(template)
    if cached is not None:
        return cached
    cursor = 0
    parts: list[str] = ["^"]
    for match in _PLACEHOLDER.finditer(template):
        parts.append(re.escape(template[cursor : match.start()]))
        # A path segment never contains "/", so a placeholder cannot swallow one.
        parts.append(f"(?P<{match.group(1)}>[^/]+)")
        cursor = match.end()
    parts.append(re.escape(template[cursor:]))
    parts.append("$")
    compiled = re.compile("".join(parts))
    _PATTERNS[template] = compiled
    return compiled


class NoRoute(LookupError):
    """No route matched the request path at all."""


class MethodNotAllowed(LookupError):
    """The path matched a route, but not for this method."""

    def __init__(self, allowed: Sequence[str]) -> None:
        self.allowed = tuple(sorted(allowed))
        super().__init__(", ".join(self.allowed))


class Router:
    """The operation table. Immutable once built."""

    __slots__ = ("_routes", "_by_operation")

    def __init__(self, routes: Iterable[Route]) -> None:
        self._routes: tuple[Route, ...] = tuple(routes)
        by_operation: dict[str, Route] = {}
        for route in self._routes:
            if route.operation_id in by_operation:
                raise ValueError(f"duplicate operationId {route.operation_id!r}")
            by_operation[route.operation_id] = route
        self._by_operation = by_operation

    @property
    def routes(self) -> tuple[Route, ...]:
        return self._routes

    @property
    def operation_ids(self) -> frozenset[str]:
        return frozenset(self._by_operation)

    def signature(self) -> frozenset[tuple[str, str, str]]:
        """``(operation_id, METHOD, template)`` for every route.

        The value the twelve-operation assertion compares against the frozen document.
        """
        return frozenset(
            (route.operation_id, route.method, route.template) for route in self._routes
        )

    def match(self, request: Request) -> tuple[Route, Request]:
        """Resolve a request to its route, binding path parameters.

        Raises :class:`NoRoute` when nothing matches the path and
        :class:`MethodNotAllowed` when the path matches under a different method. The
        two are distinct because the edge answers them differently.
        """
        allowed: list[str] = []
        for route in self._routes:
            found = route.pattern.match(request.path)
            if found is None:
                continue
            if route.method != request.method:
                allowed.append(route.method)
                continue
            return route, request.with_path_params(found.groupdict())
        if allowed:
            raise MethodNotAllowed(allowed)
        raise NoRoute(request.path)
