"""`W55A-SEAL-01`: :class:`StreamingWireResponse` keeps the wire contract of ``WireResponse``.

Container-free: the response is driven through ASGI directly, with a recording ``send``, and
through a FastAPI application carrying the real correlation middleware. What is asserted is
the thing `W55-PLAN.md` section A3.5 requires of the seal:

* the header list is exactly the one written -- names in the written case, in the written
  order, nothing appended by Starlette -- and ``X-Correlation-Id`` still comes last;
* the body is sent chunk by chunk after the status line, and the iterator is not consumed
  before ``http.response.start`` is sent (so nothing can refuse after the status line except
  by stopping short);
* :func:`streamed_content_response` answers ``200`` and ``206`` with the header order
  ``streamDocumentVersionContent`` has always answered with, which records 14, 15 and 31 pin.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from typing import Any

from fastapi import FastAPI
from starlette.testclient import TestClient

from auditmanager.api.routers.correlation import CorrelationMiddleware
from auditmanager.api.routers.wire import (
    StreamingWireResponse,
    WireResponse,
    streamed_content_response,
)
from auditmanager.api.schemas.content import PDF_MEDIA_TYPE, StreamedContent


def _drive(response: Any) -> list[dict[str, Any]]:
    """Run one response as an ASGI app and return every message it sent."""
    sent: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        await asyncio.sleep(3600)
        return {"type": "http.disconnect"}

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    scope = {"type": "http", "asgi": {"spec_version": "2.4"}, "method": "GET", "path": "/"}
    asyncio.run(response(scope, receive, send))
    return sent


def test_the_header_list_is_exactly_the_written_one() -> None:
    headers = (
        ("Content-Type", PDF_MEDIA_TYPE),
        ("Content-Length", "6"),
        ("Accept-Ranges", "bytes"),
    )
    sent = _drive(StreamingWireResponse(200, headers, iter([b"abc", b"def"])))
    start = sent[0]
    assert start["type"] == "http.response.start" and start["status"] == 200
    assert start["headers"] == [
        (b"Content-Type", PDF_MEDIA_TYPE.encode()),
        (b"Content-Length", b"6"),
        (b"Accept-Ranges", b"bytes"),
    ]


def test_the_same_list_as_the_buffered_response_writes() -> None:
    headers = (("Content-Type", PDF_MEDIA_TYPE), ("Content-Length", "3"))
    buffered = WireResponse(200, headers, b"abc")
    streamed = StreamingWireResponse(200, headers, iter([b"abc"]))
    assert streamed.raw_headers == buffered.raw_headers


def test_the_body_is_sent_chunk_by_chunk_after_the_status_line() -> None:
    order: list[str] = []

    def chunks() -> Iterator[bytes]:
        order.append("first chunk requested")
        yield b"%PDF-"
        yield b"1.7"

    response = StreamingWireResponse(
        200, (("Content-Type", PDF_MEDIA_TYPE), ("Content-Length", "8")), chunks()
    )
    assert order == [], "the iterator was consumed before the response was sent"
    sent = _drive(response)
    bodies = [message for message in sent if message["type"] == "http.response.body"]
    assert [message["body"] for message in bodies] == [b"%PDF-", b"1.7", b""]
    assert [message["more_body"] for message in bodies] == [True, True, False]
    assert order == ["first chunk requested"]


def test_a_stream_that_stops_short_sends_fewer_bytes_than_it_declared() -> None:
    """The R-115 mechanism the content lane relies on: the status line is already sent,
    so a full read that finds a digest mismatch can only stop, and the client sees a body
    shorter than ``Content-Length``."""

    def chunks() -> Iterator[bytes]:
        yield b"0123"
        raise RuntimeError("storage_integrity_error")

    response = StreamingWireResponse(
        200, (("Content-Type", PDF_MEDIA_TYPE), ("Content-Length", "8")), chunks()
    )
    sent: list[dict[str, Any]] = []

    async def run() -> None:
        async def receive() -> dict[str, Any]:
            await asyncio.sleep(3600)
            return {"type": "http.disconnect"}

        async def send(message: dict[str, Any]) -> None:
            sent.append(message)

        try:
            await response({"type": "http", "asgi": {"spec_version": "2.4"}}, receive, send)
        except RuntimeError:
            pass

    asyncio.run(run())
    delivered = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
    assert sent[0]["status"] == 200
    assert delivered == b"0123" and len(delivered) < 8
    assert not any(
        m["type"] == "http.response.body" and m.get("more_body") is False for m in sent
    ), "a stream that failed must not be closed as complete"


def test_a_whole_object_answers_200_in_the_recorded_order() -> None:
    content = StreamedContent(PDF_MEDIA_TYPE, 8, None, iter([b"%PDF-1.7"]))
    response = streamed_content_response(content)
    assert response.status_code == 200
    assert response.raw_headers == [
        (b"Content-Type", b"application/pdf"),
        (b"Content-Length", b"8"),
        (b"Accept-Ranges", b"bytes"),
    ]


def test_a_window_answers_206_with_its_range_before_accept_ranges() -> None:
    content = StreamedContent(PDF_MEDIA_TYPE, 100, (10, 19), iter([b"x" * 10]))
    response = streamed_content_response(content)
    assert response.status_code == 206
    assert response.raw_headers == [
        (b"Content-Type", b"application/pdf"),
        (b"Content-Length", b"10"),
        (b"Content-Range", b"bytes 10-19/100"),
        (b"Accept-Ranges", b"bytes"),
    ]


def test_the_correlation_header_is_still_appended_last() -> None:
    app = FastAPI()
    app.add_middleware(CorrelationMiddleware)

    @app.get("/content")
    def content() -> StreamingWireResponse:
        return streamed_content_response(
            StreamedContent(PDF_MEDIA_TYPE, 6, None, iter([b"abc", b"def"]))
        )

    with TestClient(app) as client:
        answer = client.get("/content")
    assert answer.status_code == 200
    assert answer.content == b"abcdef"
    names = [name.decode("latin-1") for name, _ in answer.headers.raw]
    assert names[:3] == ["Content-Type", "Content-Length", "Accept-Ranges"]
    assert names[-1].lower() == "x-correlation-id"
