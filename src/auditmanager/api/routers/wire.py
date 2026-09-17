"""How a response leaves this edge: the exact header list, in the exact order.

`W13-BASE` captured 33 responses through the hand-rolled edge and the wave must reproduce
those bytes. Two of the things it captured are not a framework's to choose:

* **the header names' case.** Starlette lowercases every header name it is handed
  (``Response.init_headers`` does ``key.lower()``), so a response built the ordinary way
  answers ``content-type`` where the baseline records ``Content-Type``. HTTP field names
  are case insensitive, so no client can tell -- but the baseline is a byte record of what
  this surface emits, and quietly re-casing it in the comparison would be hiding a
  difference rather than not having one;
* **the order.** The baseline records ``Content-Type``, ``Content-Length``, then the
  operation's own headers, then ``X-Correlation-Id`` last. Starlette appends
  ``content-length`` and ``content-type`` *after* whatever it was given.

:class:`WireResponse` therefore writes ``raw_headers`` itself. Everything above it -- the
routers, the exception handlers -- states the header list it wants and gets exactly that.
``X-Correlation-Id`` is the one header no route writes: the correlation middleware appends
it to every response that does not already carry one, which is what puts it last.
"""

from __future__ import annotations

import json
from typing import Any, Final, Sequence

from starlette.responses import Response

__all__ = ["JSON_MEDIA_TYPE", "WireResponse", "encode_json", "json_response"]

#: The frozen document declares ``application/json`` with no parameters on every JSON
#: response. The baseline records exactly that string.
JSON_MEDIA_TYPE: Final[str] = "application/json"


def encode_json(body: Any) -> bytes:
    """Render a body the way this surface has always rendered one.

    ``ensure_ascii=False`` and the **default** separators, ``", "`` and ``": "``. That is
    not a style preference here: it is what the 33 committed records contain, byte for
    byte. FastAPI's own ``JSONResponse`` uses the compact ``(",", ":")`` separators, so a
    response rendered through it would differ from every recorded body in every case that
    has more than one property -- a difference with no meaning, reported by the safety net
    that exists to catch differences that do.
    """
    return json.dumps(body, ensure_ascii=False).encode("utf-8")


class WireResponse(Response):
    """A response whose header list is exactly the one the caller wrote.

    Subclasses ``starlette.responses.Response`` so that everything downstream -- the
    background-task protocol, the ASGI send -- is the framework's. Only
    :meth:`init_headers` is replaced, and only to stop the name folding and the
    reordering.
    """

    def __init__(
        self,
        status_code: int,
        headers: Sequence[tuple[str, str]],
        content: bytes = b"",
    ) -> None:
        self._wire_headers: tuple[tuple[str, str], ...] = tuple(headers)
        super().__init__(content=content, status_code=status_code)

    def init_headers(self, headers: Any = None) -> None:  # noqa: D102 - see class docstring
        self.raw_headers = [
            (name.encode("latin-1"), value.encode("latin-1"))
            for name, value in self._wire_headers
        ]


def json_response(status: int, payload: bytes) -> WireResponse:
    """``Content-Type`` then ``Content-Length``, which is the recorded order."""
    return WireResponse(
        status,
        (
            ("Content-Type", JSON_MEDIA_TYPE),
            ("Content-Length", str(len(payload))),
        ),
        payload,
    )
