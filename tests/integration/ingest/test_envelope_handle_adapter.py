"""The upload's file handle reaches the service as the handle it is: unread, unchanged.

`W55B-SEAL-01` made ``DocumentPort.upload_document`` take the multipart part's file handle
and `DocumentAdapter` read it whole (``content.read()``) before calling the service, with a
test that pinned exactly that. `W55B-STREAM-01` removes the read. This file is the test that
replaced the pin: the adapter passes **the same object** on and reads from it only what it
needs to choose the service's entry -- the four magic bytes (`W55B-INGEST-01`: a ZIP is a
portal bundle, anything else is still a bare PDF until the last step of that lane), after
which the handle is back at its start. So the only other reads of the upload are the
envelope's and the store's streaming copy.

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
    """What the two upload entries are asked, and nothing they would do."""

    def __init__(self) -> None:
        self.asked: dict[str, Any] = {}
        self.entry = ""

    def upload_single_pdf(self, **kwargs: Any) -> Any:
        self.asked, self.entry = kwargs, "upload_single_pdf"
        raise RuntimeError("stop after the call; the outcome is not under test")

    def upload_bundle(self, **kwargs: Any) -> Any:
        self.asked, self.entry = kwargs, "upload_bundle"
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


def test_the_adapter_hands_the_service_the_handle_it_was_given_and_reads_four_bytes_of_it() -> None:
    handle = CountingHandle(b"PK\x03\x04 a bundle that nobody has read")
    service = RecordingService()

    _upload(handle, service)

    assert service.asked["content"] is handle, (
        f"the service received {type(service.asked['content']).__name__}, not the handle"
    )
    assert handle.content_reads == ["read(4)"], (
        f"the adapter read more than the magic bytes: {handle.content_reads}"
    )
    assert handle.tell() == 0, "the adapter left the handle past its start"


@pytest.mark.parametrize(
    ("payload", "entry"),
    [
        (b"PK\x03\x04 a local header", "upload_bundle"),
        (b"PK\x05\x06" + bytes(18), "upload_bundle"),
        (b"PK\x07\x08 spanned", "upload_bundle"),
        (b"%PDF-1.7\n a bare pdf", "upload_single_pdf"),
        (b"hello", "upload_single_pdf"),
        (b"", "upload_single_pdf"),
    ],
)
def test_a_zip_is_a_bundle_and_anything_else_is_still_the_single_pdf_entry(
    payload: bytes, entry: str
) -> None:
    """Routed by the magic bytes, never by the label or the name (the browser sends
    ``application/zip``, ``application/x-zip-compressed`` or nothing). The bare-PDF branch
    is the one the last step of `W55B-INGEST-01` removes."""
    service = RecordingService()
    _upload(CountingHandle(payload), service, source_filename="whatever.pdf")
    assert service.entry == entry


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
    assert service.entry == "upload_single_pdf"
    assert asked["source_filename"] == "bundle.zip"
    assert asked["display_title"] == "Мой документ"
    assert str(asked["project_uid"]) == PROJECT
    assert str(asked["idempotency_key"]) == "k" * 8


def test_a_missing_title_and_name_still_fall_back_as_they_did() -> None:
    service = RecordingService()
    _upload(CountingHandle(b"x"), service, source_filename="", display_title=None)
    assert service.asked["source_filename"] == "upload.pdf"
    assert service.asked["display_title"] == "upload.pdf"


def test_a_bundle_with_no_title_leaves_the_title_to_the_service() -> None:
    """The bundle's own PDF name is the better default title, and only the service has read
    the archive: the adapter passes ``None`` instead of the ZIP's name."""
    service = RecordingService()
    _upload(CountingHandle(b"PK\x03\x04x"), service, source_filename="export.zip", display_title=None)
    assert service.entry == "upload_bundle"
    assert service.asked["display_title"] is None
    assert service.asked["source_filename"] == "export.zip"
