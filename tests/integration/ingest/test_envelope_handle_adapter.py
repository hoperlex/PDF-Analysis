"""The upload's file handle reaches the service as the handle it is: unread, unchanged.

`W55B-SEAL-01` made ``DocumentPort.upload_document`` take the multipart part's file handle
and `DocumentAdapter` read it whole (``content.read()``) before calling the service, with a
test that pinned exactly that. `W55B-STREAM-01` removes the read. This file is the test that
replaced the pin: the adapter passes **the same object** on, and asks it for nothing -- so
the only reads of the upload are the envelope's (a header, a digest in chunks, PDFium's
blocks) and the store's streaming copy.

No database, no object store: the service is a stand-in that records its arguments, and the
module says so by overriding the two autouse fixtures this directory's ``conftest.py`` would
otherwise start.
"""

from __future__ import annotations

import io
from typing import Any

import pytest

from auditmanager.bootstrap.adapters import DocumentAdapter

PROJECT = "prj_01ARZ3NDEKTSV4RRFFQ69G5FAV"


@pytest.fixture(scope="session", autouse=True)
def lane_environment() -> None:  # type: ignore[override]
    """Overrides ``conftest.lane_environment``: this module reaches no service."""


@pytest.fixture(autouse=True)
def clean_tables() -> None:  # type: ignore[override]
    """Overrides ``conftest.clean_tables``: there is no database to empty."""


class CountingHandle(io.BytesIO):
    """A handle that remembers every call that would read its content."""

    def __init__(self, payload: bytes) -> None:
        super().__init__(payload)
        self.content_reads: list[str] = []

    def read(self, size: int | None = -1) -> bytes:
        self.content_reads.append(f"read({size})")
        return super().read(size)

    def read1(self, size: int = -1) -> bytes:
        self.content_reads.append(f"read1({size})")
        return super().read1(size)

    def readinto(self, buffer: Any) -> int:
        self.content_reads.append("readinto")
        return super().readinto(buffer)

    def getvalue(self) -> bytes:
        self.content_reads.append("getvalue")
        return super().getvalue()


class RecordingService:
    """What ``IngestService.upload_single_pdf`` is asked, and nothing it would do."""

    def __init__(self) -> None:
        self.asked: dict[str, Any] = {}

    def upload_single_pdf(self, **kwargs: Any) -> Any:
        self.asked = kwargs
        raise RuntimeError("stop after the call; the outcome is not under test")


def _upload(handle: Any, service: RecordingService, **overrides: Any) -> None:
    adapter = DocumentAdapter(service)
    arguments: dict[str, Any] = {
        "project_uid": PROJECT,
        "content": handle,
        "source_filename": "bundle.zip",
        "display_title": None,
        "idempotency_key": "k" * 8,
    }
    arguments.update(overrides)
    with pytest.raises(RuntimeError):
        adapter.upload_document(**arguments)


def test_the_adapter_hands_the_service_the_handle_it_was_given_and_reads_none_of_it() -> None:
    handle = CountingHandle(b"PK\x03\x04 a bundle that nobody has read")
    service = RecordingService()

    _upload(handle, service)

    assert service.asked["content"] is handle, (
        f"the service received {type(service.asked['content']).__name__}, not the handle"
    )
    assert handle.content_reads == [], f"the adapter read the upload: {handle.content_reads}"
    assert handle.tell() == 0, "the adapter moved the handle"


def test_nothing_else_about_the_call_changed() -> None:
    """The handle is the only argument that moved: the rest is what the port was given."""
    service = RecordingService()
    _upload(CountingHandle(b"x"), service, display_title="Мой документ", section=None)
    asked = dict(service.asked)
    asked.pop("content")
    assert sorted(asked) == [
        "display_title",
        "idempotency_key",
        "project_uid",
        "section",
        "source_filename",
    ]
    assert asked["source_filename"] == "bundle.zip"
    assert asked["display_title"] == "Мой документ"
    assert str(asked["project_uid"]) == PROJECT
    assert str(asked["idempotency_key"]) == "k" * 8


def test_a_missing_title_and_name_still_fall_back_as_they_did() -> None:
    service = RecordingService()
    _upload(CountingHandle(b"x"), service, source_filename="", display_title=None)
    assert service.asked["source_filename"] == "upload.pdf"
    assert service.asked["display_title"] == "upload.pdf"
