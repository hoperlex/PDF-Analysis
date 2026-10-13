"""An upload handed over as a file handle is published from the handle, and only from it.

`W55B-STREAM-01` made the upload a file handle end to end; `W55B-INGEST-01` carries that through a
portal bundle. ``IngestService.upload_bundle`` takes ``bytes | BinaryIO``. For a handle the whole
chain -- the archive reader, the envelope's PDFium parse, the store's staging, the verification
read-back -- has to work from files without a copy of the upload in memory, and the published
version has to be the same version the bytes would have given. Real PostgreSQL and real MinIO, as
the rest of this directory; the store is wrapped only to *watch* what it is given, never to
change it.

What each test is for:

* the store is handed **file handles** for the members, each at its start -- never a ``bytes`` --
  and the digests and sizes it is told are the members' own;
* the handle the caller passes may stand anywhere: the reader starts from the beginning;
* a version published from a handle is identical, field for field and byte for byte, to one
  published from the bytes of the same archive, and its stored objects read back whole;
* a refused upload publishes nothing, wherever in the envelope it was refused;
* an identical upload replayed from a handle is replayed, not published twice.
"""

from __future__ import annotations

import hashlib
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import pytest

from auditmanager.ingest import MAX_BYTES
from auditmanager.shared.errors import DomainError
from portal_bundle import generated  # tools/fixtures, put on the path by this directory's conftest
from tests.integration.ingest.bundle_support import bundle_around, committed
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
                "role": str(kwargs["role"]),
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


def _upload(service: Any, project: Any, content: Any, key: Any, label: str, **overrides: Any):
    arguments = {
        "project_uid": project.project_uid,
        "content": content,
        "source_filename": "baseline.zip",
        "display_title": "From a handle",
        "idempotency_key": key(label),
    }
    arguments.update(overrides)
    return service.upload_bundle(**arguments)


def test_the_store_is_handed_file_handles_at_their_start_and_the_members_own_digests(
    watched, project, baseline_bundle, baseline_pdf, key
) -> None:
    service, watching = watched
    handle = _spooled(baseline_bundle)
    try:
        outcome = _upload(service, project, handle, key, "handle")
    finally:
        handle.close()

    # The PDF first, then the block list and the markdown: the order of publication.
    assert [item["role"] for item in watching.staged] == [
        "source_document", "source_structured_companion", "source_markdown",
    ]
    for item in watching.staged:
        assert not isinstance(item["source"], (bytes, bytearray)), (
            f"the store was handed a {item['type'].__name__}"
        )
        assert item["position"] == 0, "staging would have uploaded from the middle of a file"
        assert item["source"] is not handle, "the archive itself was staged, not a member"
    pdf = watching.staged[0]
    assert pdf["declared_sha256"] == hashlib.sha256(baseline_pdf).hexdigest()
    assert pdf["declared_size"] == len(baseline_pdf)
    assert outcome.version.byte_size == len(baseline_pdf)


@pytest.mark.parametrize("where", ["end", "middle"])
def test_the_upload_handle_may_stand_anywhere_the_reader_starts_from_the_beginning(
    watched, project, baseline_bundle, key, where
) -> None:
    service, _watching = watched
    handle = _spooled(baseline_bundle)
    handle.seek(0, 2) if where == "end" else handle.seek(len(baseline_bundle) // 2)
    try:
        outcome = _upload(service, project, handle, key, f"left-{where}")
    finally:
        handle.close()
    assert outcome.version.page_count == 8


def test_a_version_published_from_a_handle_is_the_version_the_bytes_would_give(
    service, project, baseline_bundle, key, tmp_path: Path
) -> None:
    from_bytes = _upload(service, project, baseline_bundle, key, "bytes", display_title="From bytes")
    path = tmp_path / "baseline.zip"
    path.write_bytes(baseline_bundle)
    with path.open("rb") as handle:
        from_handle = _upload(service, project, handle, key, "file", display_title="From a file")

    a, b = from_bytes.version, from_handle.version
    assert (a.sha256, a.byte_size, a.page_count, a.media_type) == (
        b.sha256,
        b.byte_size,
        b.page_count,
        b.media_type,
    )
    assert (a.text_character_count, a.textless_pages, a.recognised_character_count) == (
        b.text_character_count, b.textless_pages, b.recognised_character_count,
    )
    assert [(e.role, e.sha256, e.size_bytes) for e in a.manifest] == [
        (e.role, e.sha256, e.size_bytes) for e in b.manifest
    ]
    with zipfile.ZipFile(path) as archive:
        pdf = archive.read(next(n for n in archive.namelist() if n.endswith(".pdf")))
    assert service.read_source_bytes(b.version_uid) == pdf


def test_a_member_larger_than_the_s3_part_size_is_staged_whole_and_verified(
    service, project, baseline_pdf, key, tmp_path: Path
) -> None:
    """A 20 MiB PDF member is past boto3's multipart threshold, so the store streams it in
    parts from the extracted file; the read-back verification still agrees on every byte."""
    padding = (b"%" + b"x" * 78 + b"\n") * (20 * 1024 * 1024 // 80)
    pdf = baseline_pdf + padding
    path = tmp_path / "big.zip"
    path.write_bytes(bundle_around(pdf))
    with path.open("rb") as handle:
        outcome = _upload(service, project, handle, key, "big", source_filename="big.zip")
    assert outcome.version.sha256 == hashlib.sha256(pdf).hexdigest()
    assert outcome.version.byte_size == len(pdf) > 20 * 1024 * 1024
    assert hashlib.sha256(service.read_source_bytes(outcome.version.version_uid)).hexdigest() == (
        outcome.version.sha256
    )


@pytest.mark.parametrize(
    ("label", "build", "constraint"),
    [
        ("image only", lambda pdf, neg: committed("image_only.zip"), "every_page_has_extractable_text"),
        ("encrypted", lambda pdf, neg: committed("encrypted.zip"), "not_encrypted"),
        # `W55B-INGEST-01`: the committed 31-page negative is valid now; 501 pages are the
        # smallest document over the ceiling, built at test time by the fixtures' generator.
        (
            "501 pages",
            lambda pdf, neg: generated.bundle_with_pages(501),
            "1 <= page_count <= 500",
        ),
        ("not a pdf", lambda pdf, neg: bundle_around(neg("not_a_pdf.txt")), "pdf_magic_bytes"),
        ("truncated", lambda pdf, neg: bundle_around(pdf[:3000]), "parseable_pdf"),
        ("not a zip", lambda pdf, neg: pdf, "portal_bundle_required"),
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
            _upload(service, project, handle, key, "refused", source_filename=f"{label}.zip")
    finally:
        handle.close()

    assert refused.value.envelope("c").details["constraint"] == constraint, label
    assert watching.staged == [], "a refused upload reached the store"
    assert set(bucket_keys()) == before_keys
    assert counts(engine) == before_counts


def test_an_oversize_sparse_handle_is_refused_without_being_read(
    watched, project, key, tmp_path: Path, bucket_keys
) -> None:
    """The case the lane's memory measurement drives over HTTP, here without the transport.

    The stand-in is one byte past the bound: a ZIP header and a hole, so it costs a few
    kilobytes of disk and is refused on its length alone."""
    service, watching = watched
    path = generated.oversize_sparse_file(tmp_path / "oversize.stand-in", MAX_BYTES + 1)
    before = set(bucket_keys())
    with path.open("rb") as handle:
        with pytest.raises(DomainError) as refused:
            _upload(service, project, handle, key, "oversize", source_filename="oversize.zip")
    assert refused.value.envelope("c").details == {
        "field": "content",
        "constraint": f"byte_size <= {MAX_BYTES}",
    }
    assert watching.staged == []
    assert set(bucket_keys()) == before


def test_an_upload_of_exactly_the_bound_is_judged_by_what_it_holds_not_by_its_size(
    watched, project, key, tmp_path: Path
) -> None:
    """The bound is inclusive: 250 MiB itself passes the size rule (this stand-in is a ZIP
    header and a hole, so the reader then cannot read it), where one byte more does not."""
    service, watching = watched
    path = generated.oversize_sparse_file(tmp_path / "at-the-bound.stand-in", MAX_BYTES)
    with path.open("rb") as handle:
        with pytest.raises(DomainError) as refused:
            _upload(service, project, handle, key, "at-bound", source_filename="at.zip")
    assert refused.value.envelope("c").details == {
        "field": "file",
        "constraint": "bundle_unreadable",
    }
    assert watching.staged == []


def test_a_non_zip_is_a_non_zip_before_it_is_anything_else_whatever_its_size(
    watched, project, key, sparse_upload
) -> None:
    """A PDF-headed file past 250 MiB is told it is not a bundle, not that it is too big: the
    first question is what the upload is, and the answer to the second (the bound) would send a
    person with the wrong file to the wrong remedy."""
    service, watching = watched
    with sparse_upload(MAX_BYTES + 1).open("rb") as handle:
        with pytest.raises(DomainError) as refused:
            _upload(service, project, handle, key, "wrong-kind", source_filename="big.pdf")
    assert refused.value.envelope("c").details == {
        "field": "file",
        "constraint": "portal_bundle_required",
    }
    assert watching.staged == []


def test_an_identical_upload_from_a_handle_is_replayed_not_published_twice(
    watched, project, baseline_bundle, key, engine
) -> None:
    service, watching = watched
    idempotency = key("replay")
    outcomes = []
    for _ in range(2):
        handle = _spooled(baseline_bundle)
        try:
            outcomes.append(
                _upload(service, project, handle, key, "replay", idempotency_key=idempotency)
            )
        finally:
            handle.close()
    assert [o.replayed for o in outcomes] == [False, True]
    assert outcomes[0].version.version_uid == outcomes[1].version.version_uid
    assert len(watching.staged) == 3, "the replay staged the members a second time"
    assert counts(engine)["document_version"] == 1
