"""An upload handed over as a file handle is published from the handle, and only from it.

`W55B-STREAM-01`. ``IngestService.upload_single_pdf`` takes ``bytes | BinaryIO``. For a
handle the whole chain -- the envelope's digest, PDFium's parse, the store's staging, the
verification read-back -- has to work from the file without a copy of it in memory, and the
published version has to be the same version the bytes would have given. Real PostgreSQL and
real MinIO, as the rest of this directory; the store is wrapped only to *watch* what it is
given, never to change it.

What each test is for:

* the store is handed the handle itself, rewound to its start, not a ``bytes``;
* a version published from a handle is identical, field for field and byte for byte, to one
  published from the bytes of the same file, and its stored object reads back whole;
* a refused handle publishes nothing, wherever in the envelope it was refused;
* an identical upload replayed from a handle is replayed, not published twice.
"""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path
from typing import Any

import pytest

from auditmanager.ingest import MAX_BYTES
from auditmanager.shared.errors import DomainError
from tests.integration.ingest.test_negative_envelope import counts  # type: ignore[import-not-found]


class WatchingStore:
    """A BlobStore that forwards everything and records what ``stage_temporary`` was given."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self.staged: list[dict[str, Any]] = []

    def stage_temporary(self, source: Any, **kwargs: Any) -> Any:
        self.staged.append(
            {
                "source": source,
                "type": type(source),
                "position": source.tell() if hasattr(source, "tell") else None,
                "declared_sha256": kwargs["declared_sha256"],
                "declared_size": kwargs["declared_size"],
            }
        )
        return self._inner.stage_temporary(source, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


@pytest.fixture
def watched(store: Any, session_factory: Any):
    from auditmanager.ingest import IngestService

    watching = WatchingStore(store)
    return IngestService(watching, session_factory=session_factory), watching


def _spooled(data: bytes) -> Any:
    """What the multipart parser hands the route: a temporary file already on disk."""
    handle = tempfile.SpooledTemporaryFile(max_size=1024)
    handle.write(data)
    handle.seek(0)
    return handle


def test_the_store_is_handed_the_handle_itself_rewound_to_its_start(
    watched, project, baseline_pdf, key
) -> None:
    service, watching = watched
    handle = _spooled(baseline_pdf)
    try:
        outcome = service.upload_single_pdf(
            project_uid=project.project_uid,
            content=handle,
            source_filename="baseline.pdf",
            display_title="From a handle",
            idempotency_key=key("handle"),
        )
    finally:
        handle.close()

    assert len(watching.staged) == 1
    staged = watching.staged[0]
    assert staged["source"] is handle, f"the store was handed a {staged['type'].__name__}"
    assert not isinstance(staged["source"], (bytes, bytearray))
    assert staged["position"] == 0, "staging would have uploaded from the middle of the file"
    assert staged["declared_sha256"] == hashlib.sha256(baseline_pdf).hexdigest()
    assert staged["declared_size"] == len(baseline_pdf)
    assert outcome.version.byte_size == len(baseline_pdf)


def test_a_version_published_from_a_handle_is_the_version_the_bytes_would_give(
    service, project, baseline_pdf, key, tmp_path: Path
) -> None:
    from_bytes = service.upload_single_pdf(
        project_uid=project.project_uid,
        content=baseline_pdf,
        source_filename="baseline.pdf",
        display_title="From bytes",
        idempotency_key=key("bytes"),
    )
    path = tmp_path / "baseline.pdf"
    path.write_bytes(baseline_pdf)
    with path.open("rb") as handle:
        from_handle = service.upload_single_pdf(
            project_uid=project.project_uid,
            content=handle,
            source_filename="baseline.pdf",
            display_title="From a file",
            idempotency_key=key("file"),
        )

    a, b = from_bytes.version, from_handle.version
    assert (a.sha256, a.byte_size, a.page_count, a.media_type) == (
        b.sha256,
        b.byte_size,
        b.page_count,
        b.media_type,
    )
    assert [(e.role, e.sha256, e.size_bytes) for e in a.manifest] == [
        (e.role, e.sha256, e.size_bytes) for e in b.manifest
    ]
    assert service.read_source_bytes(b.version_uid) == baseline_pdf


def test_a_handle_larger_than_the_s3_part_size_is_staged_whole_and_verified(
    service, project, key, tmp_path: Path
) -> None:
    """A 20 MiB document is past boto3's multipart threshold, so the store streams it in
    parts from the handle; the read-back verification still agrees on every byte."""
    from tests.integration.ingest.test_envelope_differential import (  # type: ignore[import-not-found]
        hand_pdf_of_size,
    )

    data = hand_pdf_of_size(20 * 1024 * 1024)
    path = tmp_path / "big.pdf"
    path.write_bytes(data)
    with path.open("rb") as handle:
        outcome = service.upload_single_pdf(
            project_uid=project.project_uid,
            content=handle,
            source_filename="big.pdf",
            display_title="Twenty mebibytes",
            idempotency_key=key("big"),
        )
    assert outcome.version.sha256 == hashlib.sha256(data).hexdigest()
    assert outcome.version.byte_size == len(data)
    assert hashlib.sha256(service.read_source_bytes(outcome.version.version_uid)).hexdigest() == (
        outcome.version.sha256
    )


@pytest.mark.parametrize(
    ("label", "build", "constraint"),
    [
        ("image only", lambda pdf, neg: neg("image_only.pdf"), "every_page_has_extractable_text"),
        ("encrypted", lambda pdf, neg: neg("encrypted.pdf"), "not_encrypted"),
        ("31 pages", lambda pdf, neg: neg("too_many_pages.pdf"), "1 <= page_count <= 30"),
        ("not a pdf", lambda pdf, neg: neg("not_a_pdf.txt"), "pdf_magic_bytes"),
        ("truncated", lambda pdf, neg: pdf[:3000], "parseable_pdf"),
        ("26 MiB", lambda pdf, neg: b"%PDF-1.7\n" + b"0" * (26 * 1024 * 1024), f"byte_size <= {MAX_BYTES}"),
    ],
)
def test_a_refused_handle_publishes_nothing(
    watched, project, baseline_pdf, negative_pdf, key, engine, bucket_keys, label, build, constraint
) -> None:
    service, watching = watched
    before_keys = set(bucket_keys())
    before_counts = counts(engine)

    handle = _spooled(build(baseline_pdf, negative_pdf))
    try:
        with pytest.raises(DomainError) as refused:
            service.upload_single_pdf(
                project_uid=project.project_uid,
                content=handle,
                source_filename=f"{label}.pdf",
                display_title="Refused",
                idempotency_key=key("refused"),
            )
    finally:
        handle.close()

    assert refused.value.envelope("c").details["constraint"] == constraint, label
    assert watching.staged == [], "a refused upload reached the store"
    assert set(bucket_keys()) == before_keys
    assert counts(engine) == before_counts


def test_an_oversize_sparse_handle_is_refused_without_being_read(
    watched, project, key, tmp_path: Path, bucket_keys
) -> None:
    """The case the lane's memory measurement drives over HTTP, here without the transport."""
    service, watching = watched
    path = tmp_path / "oversize.bin"
    with path.open("wb") as out:
        out.write(b"%PDF-1.7\n")
        out.truncate(250 * 1024 * 1024)
    before = set(bucket_keys())
    with path.open("rb") as handle:
        with pytest.raises(DomainError) as refused:
            service.upload_single_pdf(
                project_uid=project.project_uid,
                content=handle,
                source_filename="oversize.pdf",
                display_title="Too big",
                idempotency_key=key("oversize"),
            )
    assert refused.value.envelope("c").details == {
        "field": "content",
        "constraint": f"byte_size <= {MAX_BYTES}",
    }
    assert watching.staged == []
    assert set(bucket_keys()) == before


def test_an_identical_upload_from_a_handle_is_replayed_not_published_twice(
    watched, project, baseline_pdf, key, engine
) -> None:
    service, watching = watched
    idempotency = key("replay")
    outcomes = []
    for _ in range(2):
        handle = _spooled(baseline_pdf)
        try:
            outcomes.append(
                service.upload_single_pdf(
                    project_uid=project.project_uid,
                    content=handle,
                    source_filename="baseline.pdf",
                    display_title="Replayed",
                    idempotency_key=idempotency,
                )
            )
        finally:
            handle.close()
    assert [o.replayed for o in outcomes] == [False, True]
    assert outcomes[0].version.version_uid == outcomes[1].version.version_uid
    assert len(watching.staged) == 1, "the replay staged the bytes a second time"
    assert counts(engine)["document_version"] == 1
