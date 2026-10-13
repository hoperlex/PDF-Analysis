"""The upload's file handle reaches the service as the handle it is: unread, unchanged.

`W55B-SEAL-01` made ``DocumentPort.upload_document`` take the multipart part's file handle
and `DocumentAdapter` read it whole (``content.read()``) before calling the service, with a
test that pinned exactly that. `W55B-STREAM-01` removes the read. This file is the test that
replaced the pin: the adapter passes **the same object** on and reads **nothing** from it
(`W55B-INGEST-01`, last step: every upload is a portal bundle and goes to the bundle entry,
which decides by the magic bytes that a bare PDF is not one). So the only reads of the upload
are the service's: the archive reader's and the store's streaming copy.

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
    """What the one upload entry is asked, and nothing it would do.

    It has no ``upload_single_pdf``: that entry was deleted by the last step of
    `W55B-INGEST-01`, so an adapter that still reached for it fails here with an
    ``AttributeError`` and not with the ``RuntimeError`` the tests below expect.
    """

    def __init__(self) -> None:
        self.asked: dict[str, Any] = {}
        self.entry = ""

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


def test_the_adapter_hands_the_service_the_handle_it_was_given_and_reads_none_of_it() -> None:
    handle = CountingHandle(b"PK\x03\x04 a bundle that nobody has read")
    service = RecordingService()

    _upload(handle, service)

    assert service.asked["content"] is handle, (
        f"the service received {type(service.asked['content']).__name__}, not the handle"
    )
    assert handle.content_reads == [], (
        f"the adapter read the upload, which is the service's to read: {handle.content_reads}"
    )
    assert handle.tell() == 0, "the adapter left the handle past its start"


@pytest.mark.parametrize(
    "payload",
    [
        b"PK\x03\x04 a local header",
        b"PK\x05\x06" + bytes(18),
        b"PK\x07\x08 spanned",
        b"%PDF-1.7\n a bare pdf",
        b"hello",
        b"",
    ],
    ids=["a ZIP local header", "an empty archive", "a spanning marker", "a bare PDF", "text", "nothing"],
)
def test_every_upload_goes_to_the_bundle_entry_whatever_it_holds(payload: bytes) -> None:
    """There is one entry. A bare PDF, text and nothing at all reach the same call as a ZIP
    does, and it is the service -- not this adapter -- that refuses what is not a bundle
    (``test_envelope_through_the_service.py``, ``test_bundle_publication.py``). Routed by
    nothing: not by the label, the name or the magic bytes."""
    service = RecordingService()
    _upload(CountingHandle(payload), service, source_filename="whatever.pdf")
    assert service.entry == "upload_bundle"


def test_the_service_has_no_single_pdf_entry_left() -> None:
    """The deletion this lane ends with, asserted on the service itself and not on a stand-in:
    the entry is gone, and so is the admission report that only it used."""
    from auditmanager.ingest import IngestService, envelope

    assert not hasattr(IngestService, "upload_single_pdf")
    assert not hasattr(IngestService, "_commit_publication")
    assert not hasattr(envelope, "probe")
    assert not hasattr(envelope, "AdmissionReport")


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
    assert service.entry == "upload_bundle"
    assert asked["source_filename"] == "bundle.zip"
    assert asked["display_title"] == "Мой документ"
    assert str(asked["project_uid"]) == PROJECT
    assert str(asked["idempotency_key"]) == "k" * 8


def test_a_missing_name_falls_back_to_a_zip_name_and_a_missing_title_stays_missing() -> None:
    """The default name says what an upload is now (``upload.zip``, it was ``upload.pdf``);
    the title is no longer defaulted to it here, because the service has read the archive and
    the PDF member's own name is the better default."""
    service = RecordingService()
    _upload(CountingHandle(b"x"), service, source_filename="", display_title=None)
    assert service.asked["source_filename"] == "upload.zip"
    assert service.asked["display_title"] is None


def test_a_bundle_with_no_title_leaves_the_title_to_the_service() -> None:
    """The bundle's own PDF name is the better default title, and only the service has read
    the archive: the adapter passes ``None`` instead of the ZIP's name."""
    service = RecordingService()
    _upload(CountingHandle(b"PK\x03\x04x"), service, source_filename="export.zip", display_title=None)
    assert service.entry == "upload_bundle"
    assert service.asked["display_title"] is None
    assert service.asked["source_filename"] == "export.zip"
