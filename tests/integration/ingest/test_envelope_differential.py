"""The pypdfium2 envelope refuses exactly as the pypdf + pdfplumber one did.

`W55B-STREAM-01` moved the admission probe's PDF checks -- structure, encryption, page
count, per-page text presence -- from ``pypdf`` and ``pdfplumber`` (18.2 s for 30 pages of
the real AR document) to ``pypdfium2`` reading the upload from a file handle (0.53 s), and
promised that **every refusal keeps its ``field``, ``constraint`` and message byte for
byte**. A promise like that is only as good as the comparison that backs it, so this file
keeps the previous implementation *here*, as the oracle, and runs the same inputs through
both:

* the committed negatives, the baseline document and every PDF in the committed bundles;
* documents written by hand for this file, one rule each: a page with no text and a page
  with only spaces, no pages at all, 501 and 31 and 30 and 1 pages (`W55B-INGEST-01` moved
  the ceilings to 500 pages and 250 MiB; the boundary at exactly 250 MiB is asserted on a
  sparse file in its own test, because the oracle would have to read it);
* encrypted documents -- one that needs a password and one that opens with an empty one;
* truncated and byte-flipped copies of the baseline.

**The oracle is itself held to the record.** ``tests/characterization/w13_baseline/records``
pins the bodies of 17, 18, 19, 20 and 21 -- the five refusals an upload can get from this
envelope -- as the API sent them before this lane. Both the oracle and the new envelope are
compared with those bytes, so an oracle edited to agree with a changed implementation would
disagree with the record.

**The rule for the inputs that are not named.** Where the old envelope accepts, the new one
accepts with the same report; where both refuse, the payloads are identical. The one
direction the comparison allows to differ is that the new parser may *accept* a damaged
document the old text extractor tripped over (``test_leniency_is_only_ever_toward_accepting``
says which way and shows it for the seeded flips). It must never refuse what the old one
accepted, and never refuse differently.

The module needs no database, no object store and no container, and says so by overriding
the two autouse fixtures this directory's ``conftest.py`` would otherwise start.
"""

from __future__ import annotations

import hashlib
import io
import json
import random
import tempfile
import threading
import tracemalloc
import warnings
import zipfile
from pathlib import Path
from typing import Any, BinaryIO, Sequence

import pytest
from pypdf import PdfWriter

from auditmanager.ingest import envelope as new_envelope
from auditmanager.ingest.envelope import AdmissionReport, validate_source_filename
from auditmanager.shared.errors import DomainError, ErrorCode

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CORPUS = REPOSITORY_ROOT / "fixtures" / "synthetic" / "ar"
RECORDS = REPOSITORY_ROOT / "tests" / "characterization" / "w13_baseline" / "records"

#: Written out, never imported from the module under test: the envelope's numbers. The
#: oracle is the *previous implementation* (pypdf and pdfplumber), and the previous
#: implementation is held to the ceilings the product has now -- `W55B-INGEST-01` raised them
#: from 25 MiB and 30 pages to 250 MiB and 500 pages, and an oracle that kept the old numbers
#: would refuse documents the envelope is meant to accept. What the comparison tests is the
#: parser, not the number.
OLD_MAX_BYTES = 250 * 1024 * 1024
OLD_MAX_PAGES = 500
OLD_MAGIC = b"%PDF-"


@pytest.fixture(scope="session", autouse=True)
def lane_environment() -> None:  # type: ignore[override]
    """Overrides ``conftest.lane_environment``: this module reaches no service."""


@pytest.fixture(autouse=True)
def clean_tables() -> None:  # type: ignore[override]
    """Overrides ``conftest.clean_tables``: there is no database to empty."""


# ---------------------------------------------------------------------------------------
# The oracle: the previous implementation, kept here and nowhere else
# ---------------------------------------------------------------------------------------


def _old_refuse(field: str, constraint: str, message: str) -> DomainError:
    return DomainError(
        ErrorCode.VALIDATION_FAILED, message=message, field=field, constraint=constraint
    )


def old_probe(content: bytes, *, source_filename: str) -> AdmissionReport:
    """``auditmanager.ingest.envelope.probe`` as it was at ``461411b6`` (pypdf, pdfplumber).

    Only the three functions that changed are copied, with their bodies unedited; the file
    name rule is unchanged code and is called, not copied.
    """
    validate_source_filename(source_filename)

    if not isinstance(content, (bytes, bytearray)):
        raise _old_refuse("content", "bytes", "The upload payload must be raw bytes.")
    data = bytes(content)

    if not data:
        raise _old_refuse("content", "non_empty", "The upload payload is empty.")

    if not data.startswith(OLD_MAGIC):
        raise _old_refuse(
            "content",
            "pdf_magic_bytes",
            "The upload payload does not begin with a PDF header, so it is not a PDF "
            "whatever its name says.",
        )

    if len(data) > OLD_MAX_BYTES:
        raise _old_refuse(
            "content",
            f"byte_size <= {OLD_MAX_BYTES}",
            "The upload payload is larger than the accepted envelope allows.",
        )

    page_count = _old_page_count(data)

    if page_count < 1 or page_count > OLD_MAX_PAGES:
        raise _old_refuse(
            "page_count",
            f"1 <= page_count <= {OLD_MAX_PAGES}",
            "The document carries more pages than the accepted envelope allows, or "
            "carries none at all.",
        )

    _old_require_text_on_every_page(data)

    return AdmissionReport(
        byte_size=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        page_count=page_count,
    )


def _old_page_count(data: bytes) -> int:
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            reader = PdfReader(io.BytesIO(data), strict=False)
            if reader.is_encrypted:
                raise _old_refuse(
                    "content",
                    "not_encrypted",
                    "The document is encrypted. This prototype accepts unencrypted "
                    "PDFs only.",
                )
            return len(reader.pages)
    except DomainError:
        raise
    except (PdfReadError, ValueError, OSError, KeyError, TypeError, RecursionError):
        raise _old_refuse(
            "content",
            "parseable_pdf",
            "The upload payload could not be parsed as a PDF document.",
        ) from None


def _old_require_text_on_every_page(data: bytes) -> None:
    import pdfplumber

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with pdfplumber.open(io.BytesIO(data)) as document:
                pages = document.pages
                if not pages:
                    raise _old_refuse(
                        "page_count",
                        f"1 <= page_count <= {OLD_MAX_PAGES}",
                        "The document carries no pages.",
                    )
                for page in pages:
                    if not (page.extract_text() or "").strip():
                        raise _old_refuse(
                            "page_text",
                            "every_page_has_extractable_text",
                            "At least one page carries no extractable embedded text. "
                            "This prototype never substitutes OCR for a text layer.",
                        )
    except DomainError:
        raise
    except Exception:
        raise _old_refuse(
            "content",
            "parseable_pdf",
            "The upload payload could not be read for its text layer.",
        ) from None


# ---------------------------------------------------------------------------------------
# What a verdict is, and the four ways the new envelope is handed an upload
# ---------------------------------------------------------------------------------------


def verdict(call: Any) -> tuple[Any, ...]:
    """Everything a caller can see of one probe: the report, or the whole refusal."""
    try:
        report = call()
    except DomainError as failure:
        envelope = failure.envelope("corr_differential")
        return (
            "refused",
            envelope.http_status,
            envelope.error_code,
            envelope.message,
            dict(envelope.details),
        )
    return ("accepted", report.byte_size, report.sha256, report.page_count, report.media_type)


def old_verdict(data: bytes) -> tuple[Any, ...]:
    return verdict(lambda: old_probe(data, source_filename="upload.pdf"))


def new_verdicts(data: bytes, directory: Path) -> dict[str, tuple[Any, ...]]:
    """The new envelope on the same bytes as a byte string, and as three kinds of handle."""
    path = directory / "upload.bin"
    path.write_bytes(data)
    results: dict[str, tuple[Any, ...]] = {}
    results["bytes"] = verdict(lambda: new_envelope.probe(data, source_filename="upload.pdf"))
    results["BytesIO"] = verdict(
        lambda: new_envelope.probe(io.BytesIO(data), source_filename="upload.pdf")
    )
    with path.open("rb") as handle:
        results["file"] = verdict(
            lambda: new_envelope.probe(handle, source_filename="upload.pdf")
        )
    with tempfile.SpooledTemporaryFile(max_size=1024) as spooled:  # rolled to disk at once
        spooled.write(data)
        spooled.seek(0)
        results["spooled"] = verdict(
            lambda: new_envelope.probe(spooled, source_filename="upload.pdf")
        )
    return results


# ---------------------------------------------------------------------------------------
# Documents written by hand: one rule each, correct cross-reference table, no library
# ---------------------------------------------------------------------------------------


def hand_pdf(pages: Sequence[str | None], *, filler: int = 0) -> bytes:
    """A valid PDF with one page per entry: ``None`` is a page with an empty content stream.

    ``filler`` adds an unreferenced stream of that many bytes, which is how a document of an
    exact size is made without changing what it says.
    """
    count = len(pages)
    objects: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: (
            "<< /Type /Pages /Kids ["
            + " ".join(f"{4 + 2 * i} 0 R" for i in range(count))
            + f"] /Count {count} >>"
        ).encode(),
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    for index, text in enumerate(pages):
        page_id, content_id = 4 + 2 * index, 5 + 2 * index
        objects[page_id] = (
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>"
        ).encode()
        stream = b"" if text is None else f"BT /F1 12 Tf 72 700 Td ({text}) Tj ET".encode()
        objects[content_id] = f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream"
    if filler:
        objects[4 + 2 * count] = (
            f"<< /Length {filler} >>\nstream\n".encode() + b"\0" * filler + b"\nendstream"
        )
    out = bytearray(b"%PDF-1.7\n")
    offsets: dict[int, int] = {}
    for number in sorted(objects):
        offsets[number] = len(out)
        out += f"{number} 0 obj\n".encode() + objects[number] + b"\nendobj\n"
    xref = len(out)
    size = max(objects) + 1
    out += f"xref\n0 {size}\n".encode() + b"0000000000 65535 f \n"
    for number in range(1, size):
        out += f"{offsets[number]:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {size} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


def hand_pdf_of_size(total: int) -> bytes:
    """A valid one-page PDF of exactly ``total`` bytes."""
    filler = max(total - len(hand_pdf(["x"])), 1)
    for _ in range(8):
        document = hand_pdf(["x"], filler=filler)
        if len(document) == total:
            return document
        filler += total - len(document)
    raise AssertionError(f"could not size a document to {total} bytes")


def encrypted_pdf(user_password: str) -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(200, 200)
    writer.encrypt(user_password=user_password, owner_password="owner-password")
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def no_page_pdf() -> bytes:
    buffer = io.BytesIO()
    PdfWriter().write(buffer)
    return buffer.getvalue()


def _committed() -> dict[str, bytes]:
    found: dict[str, bytes] = {"ar_baseline.pdf": (CORPUS / "ar_baseline.pdf").read_bytes()}
    for path in sorted((CORPUS / "negative").iterdir()):
        # `oversize.pdf` and `too_many_pages.pdf` are generated at test time now, not committed.
        found[f"negative/{path.name}"] = path.read_bytes()
    for archive in sorted((CORPUS / "bundles").glob("*.zip")):
        with zipfile.ZipFile(archive) as bundle:
            for member in bundle.namelist():
                if member.endswith(".pdf"):
                    found[f"bundles/{archive.name}/{member}"] = bundle.read(member)
    return found


def _written() -> dict[str, bytes]:
    return {
        "hand/one page": hand_pdf(["Hello world"]),
        "hand/thirty pages": hand_pdf([f"Page {n}" for n in range(1, 31)]),
        "hand/thirty one pages": hand_pdf([f"Page {n}" for n in range(1, 32)]),
        "hand/five hundred and one pages": hand_pdf([f"Page {n}" for n in range(1, 502)]),
        "hand/no pages": hand_pdf([]),
        "hand/an empty page": hand_pdf(["Hello", None]),
        "hand/a page of spaces only": hand_pdf(["Hello", "     "]),
        "hand/the last page has no text": hand_pdf(["a", "b", "c", None]),
        "pypdf/no pages": no_page_pdf(),
        "pypdf/encrypted, password needed": encrypted_pdf("secret"),
        "pypdf/encrypted, empty user password": encrypted_pdf(""),
        "size/a few mebibytes": hand_pdf_of_size(3 * 1024 * 1024),
    }


def _damaged() -> dict[str, bytes]:
    base = (CORPUS / "ar_baseline.pdf").read_bytes()
    found: dict[str, bytes] = {}
    for cut in (5, 9, 100, 1000, 3000, 20000, 50000, len(base) - 100, len(base) - 1):
        found[f"truncated at {cut}"] = base[:cut]
    found["a header and nothing else"] = b"%PDF-"
    found["a header and zeros"] = b"%PDF-1.7\n" + b"\0" * 1000
    found["a header and prose"] = b"%PDF-1.7\nthis is not a pdf at all"
    found["not a pdf"] = b"hello"
    found["empty"] = b""
    generator = random.Random(7)
    for index in range(12):
        flipped = bytearray(base)
        for _ in range(generator.choice([1, 5, 50])):
            flipped[generator.randrange(len(flipped))] = generator.randrange(256)
        found[f"seeded byte flips {index}"] = bytes(flipped)
    return found


NAMED = {**_committed(), **_written()}
DAMAGED = _damaged()


# ---------------------------------------------------------------------------------------
# The comparison
# ---------------------------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(NAMED))
def test_every_named_input_gets_the_old_answer_from_every_way_of_being_handed_it(
    name: str, tmp_path: Path
) -> None:
    """Byte for byte: status, code, message and every detail, or the same report."""
    data = NAMED[name]
    expected = old_verdict(data)
    for how, found in new_verdicts(data, tmp_path).items():
        assert found == expected, (
            f"{name}: handed over as {how}, the new envelope answers\n  {found}\nwhere the "
            f"previous one answered\n  {expected}"
        )


@pytest.mark.parametrize("name", sorted(DAMAGED))
def test_a_damaged_input_is_never_refused_differently_or_refused_after_being_accepted(
    name: str, tmp_path: Path
) -> None:
    """Damage is where two parsers are most likely to part ways, so the rule is the weak one
    (see the module docstring): equal where the old one refuses, and never worse."""
    data = DAMAGED[name]
    expected = old_verdict(data)
    answers = new_verdicts(data, tmp_path)
    assert len({repr(answer) for answer in answers.values()}) == 1, (
        f"{name}: the answer depends on how the upload was handed over: {answers}"
    )
    found = answers["file"]
    if expected[0] == "accepted":
        assert found == expected, f"{name}: the old envelope accepted it; now {found}"
    elif found[0] == "refused":
        assert found == expected, (
            f"{name}: both refuse, but not alike:\n  new {found}\n  old {expected}"
        )


def test_leniency_is_only_ever_toward_accepting(tmp_path: Path) -> None:
    """Measured, not assumed: of the seeded flips exactly the documents the old text extractor
    tripped over may now pass, and each one then still has text on every page."""
    leniencies = []
    for name, data in sorted(DAMAGED.items()):
        old = old_verdict(data)
        new = new_verdicts(data, tmp_path)["file"]
        if old != new:
            leniencies.append((name, old, new))
    for name, old, new in leniencies:
        assert old[0] == "refused" and new[0] == "accepted", (name, old, new)
        assert old[4] == {
            "field": "content",
            "constraint": "parseable_pdf",
        }, f"{name}: only a parse failure may turn into an acceptance: {old}"
        assert new[3] >= 1


# ---------------------------------------------------------------------------------------
# The oracle and the new envelope, both against the bytes the API recorded
# ---------------------------------------------------------------------------------------


def _recorded(record: str) -> tuple[str, dict[str, Any]]:
    path = next(RECORDS.glob(f"{record}-*.json"))
    body = json.loads(json.loads(path.read_text(encoding="utf-8"))["response"]["body"]["text"])
    return body["message"], body["details"]


@pytest.mark.parametrize(
    ("record", "fixture"),
    [
        ("17", "negative/not_a_pdf.txt"),
        ("19", "negative/encrypted.pdf"),
        ("20", "hand/five hundred and one pages"),
        ("21", "negative/image_only.pdf"),
    ],
)
def test_the_oracle_and_the_new_envelope_both_say_what_the_record_says(
    record: str, fixture: str, tmp_path: Path
) -> None:
    message, details = _recorded(record)
    data = NAMED[fixture]
    expected = ("refused", 422, "validation_failed", message, details)
    assert old_verdict(data) == expected, "the oracle drifted from the record"
    for how, found in new_verdicts(data, tmp_path).items():
        assert found == expected, f"{fixture} as {how}"


def test_the_size_refusal_of_record_18_is_the_same_bytes(tmp_path: Path) -> None:
    """Record 18's body is the envelope's size refusal for an upload past 250 MiB: the part is
    a PDF header and padding, past the bound and parsed by nobody. The record's request is a
    sparse file one byte over the bound (`W55B-INGEST-01` moved it from a 26 MiB body); its
    response differs from the earlier one in the number alone."""
    message, details = _recorded("18")
    path = tmp_path / "over.bin"
    with path.open("wb") as out:
        out.write(b"%PDF-1.7\n")
        out.truncate(OLD_MAX_BYTES + 1)
    expected = ("refused", 422, "validation_failed", message, details)
    # The oracle takes bytes: the whole sparse file, once. It refuses on its length alone.
    assert old_verdict(path.read_bytes()) == expected
    with path.open("rb") as handle:
        found = verdict(lambda: new_envelope.probe(handle, source_filename="a.pdf"))
    assert found == expected


# ---------------------------------------------------------------------------------------
# What the new envelope promises beyond the old one
# ---------------------------------------------------------------------------------------


class RecordingHandle:
    """A readable handle that remembers how it was read.

    Delegates to a real file, counts bytes, keeps the largest single read, and calls
    ``on_read(kind)`` -- ``"read"`` or ``"readinto"`` -- before each, so a test can assert
    something about the moment of the read.
    """

    def __init__(self, inner: BinaryIO, on_read: Any = None) -> None:
        self._inner = inner
        self.largest_read = 0
        self.bytes_read = 0
        self.unbounded_reads = 0
        self.reads = 0
        self._on_read = on_read

    def _note(self, size: int | None, kind: str) -> None:
        if self._on_read is not None:
            self._on_read(kind)
        self.reads += 1
        if size is None or size < 0:
            self.unbounded_reads += 1
        else:
            self.largest_read = max(self.largest_read, size)

    def read(self, size: int = -1) -> bytes:
        self._note(size, "read")
        data = self._inner.read(size)
        self.bytes_read += len(data)
        return data

    def readinto(self, buffer: Any) -> int:
        self._note(len(buffer), "readinto")
        count = self._inner.readinto(buffer)
        self.bytes_read += count or 0
        return count

    def seek(self, offset: int, whence: int = 0) -> int:
        return self._inner.seek(offset, whence)

    def tell(self) -> int:
        return self._inner.tell()

    def seekable(self) -> bool:
        return True


def _file_of(data: bytes, directory: Path) -> Path:
    path = directory / "upload.bin"
    path.write_bytes(data)
    return path


def test_the_handle_is_left_at_its_start_ready_to_be_staged(tmp_path: Path) -> None:
    path = _file_of(NAMED["ar_baseline.pdf"], tmp_path)
    with path.open("rb") as handle:
        report = new_envelope.probe(handle, source_filename="a.pdf")
        assert handle.tell() == 0, "the staging step would upload from the middle of the file"
        assert handle.read() == NAMED["ar_baseline.pdf"]
    assert report.sha256 == hashlib.sha256(NAMED["ar_baseline.pdf"]).hexdigest()


def test_no_read_is_unbounded_or_larger_than_one_chunk(tmp_path: Path) -> None:
    """The digest is computed while streaming: nothing asks the handle for all of it, or for
    more than the chunk the digest loop and PDFium's block reads use."""
    data = hand_pdf_of_size(4 * 1024 * 1024)
    path = _file_of(data, tmp_path)
    with path.open("rb") as inner:
        handle = RecordingHandle(inner)
        report = new_envelope.probe(handle, source_filename="a.pdf")  # type: ignore[arg-type]
    assert report.sha256 == hashlib.sha256(data).hexdigest()
    assert handle.unbounded_reads == 0, "the envelope read the whole handle in one call"
    assert handle.largest_read <= 1024 * 1024, handle.largest_read
    assert handle.bytes_read >= len(data), "the digest did not cover the whole upload"


def test_peak_python_memory_is_a_small_fraction_of_the_upload(tmp_path: Path) -> None:
    """A 24 MiB document is probed from a file with a Python-level peak far below its size.

    ``tracemalloc`` sees Python allocations only, which is the point: nothing here may build
    a ``bytes`` of the upload, a ``bytearray`` of it, or a join of its chunks. The ceiling
    leaves room for one digest chunk, PDFium's block buffers and the parse's own objects.
    """
    size = 24 * 1024 * 1024
    path = _file_of(hand_pdf_of_size(size), tmp_path)
    tracemalloc.start()
    try:
        with path.open("rb") as handle:
            new_envelope.probe(handle, source_filename="a.pdf")
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert peak < 4 * 1024 * 1024, (
        f"probing a {size}-byte upload peaked at {peak} bytes of Python memory; the digest "
        "and the parse are meant to stream"
    )


def test_an_oversize_upload_is_refused_after_reading_its_header_and_nothing_else(
    tmp_path: Path,
) -> None:
    """Rule 4 comes before any parse or hash: 250 MiB and a byte of sparse file, five bytes read."""
    path = tmp_path / "oversize.bin"
    with path.open("wb") as out:
        out.write(b"%PDF-1.7\n")
        out.truncate(OLD_MAX_BYTES + 1)
    with path.open("rb") as inner:
        handle = RecordingHandle(inner)
        with pytest.raises(DomainError) as refused:
            new_envelope.probe(handle, source_filename="a.pdf")  # type: ignore[arg-type]
    details = refused.value.envelope("c").details
    assert details == {"field": "content", "constraint": f"byte_size <= {OLD_MAX_BYTES}"}
    assert handle.bytes_read == 5, f"{handle.bytes_read} bytes were read before the size refusal"


def test_pdfium_is_only_ever_called_with_its_lock_held(tmp_path: Path) -> None:
    """PDFium is not thread-safe and the route runs in a thread pool.

    Only PDFium calls ``readinto`` on the handle (the envelope's own reads are ``read``), so
    the lock state at each ``readinto`` is the lock state of a call into PDFium: it must be
    held every time, and PDFium must have asked at least once or the test proves nothing.
    """
    path = _file_of(NAMED["ar_baseline.pdf"], tmp_path)
    seen: list[tuple[str, bool]] = []
    with path.open("rb") as inner:
        handle = RecordingHandle(
            inner, on_read=lambda kind: seen.append((kind, new_envelope.PDFIUM_LOCK.locked()))
        )
        new_envelope.probe(handle, source_filename="a.pdf")  # type: ignore[arg-type]
    pdfium = [locked for kind, locked in seen if kind == "readinto"]
    assert pdfium, "PDFium never read through the handle"
    assert all(pdfium), f"PDFium read a block without holding the lock: {seen}"
    assert not any(locked for kind, locked in seen if kind == "read"), (
        "the magic-byte and digest reads took the PDFium lock, which only PDFium needs"
    )


def test_two_probes_in_two_threads_do_not_overlap_in_pdfium(tmp_path: Path) -> None:
    """The lock serialises: while one thread's blocks are being read for PDFium, no other
    thread's are -- judged from the reads themselves, not from the lock's state, so a probe
    that stopped taking the lock would be seen."""
    path = _file_of(NAMED["ar_baseline.pdf"], tmp_path)
    active = 0
    overlapped = threading.Event()
    guard = threading.Lock()

    def on_read(kind: str) -> None:
        nonlocal active
        if kind != "readinto":  # only PDFium reads with readinto
            return
        with guard:
            active += 1
            if active > 1:
                overlapped.set()
        threading.Event().wait(0.002)
        with guard:
            active -= 1

    def work() -> None:
        for _ in range(8):
            with path.open("rb") as inner:
                new_envelope.probe(RecordingHandle(inner, on_read=on_read), source_filename="a.pdf")  # type: ignore[arg-type]

    threads = [threading.Thread(target=work) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=120)
    assert not overlapped.is_set(), "two threads were inside PDFium at once"


def test_a_failed_load_never_borrows_the_last_error_of_an_earlier_one() -> None:
    """The defect the first draft of this envelope had, kept as a regression.

    PDFium sets its *last error* only when a load fails, and ``pypdfium2.PdfDocument`` reads
    it to explain a load that returned no pages. After an upload refused as encrypted (error
    4) a document that simply has no pages was explained by that stale 4 and refused as
    ``not_encrypted`` instead of ``page_count``. The order below is the failing one.
    """
    sequence = [
        encrypted_pdf("secret"),
        no_page_pdf(),
        NAMED["negative/image_only.pdf"],
        no_page_pdf(),
        b"%PDF-1.7\nthis is not a pdf at all",
        no_page_pdf(),
        encrypted_pdf("secret"),
        hand_pdf([]),
    ]
    found = [verdict(lambda d=d: new_envelope.probe(d, source_filename="a.pdf")) for d in sequence]
    constraints = [entry[4]["constraint"] for entry in found]
    assert constraints == [
        "not_encrypted",
        "1 <= page_count <= 500",
        "every_page_has_extractable_text",
        "1 <= page_count <= 500",
        "parseable_pdf",
        "1 <= page_count <= 500",
        "not_encrypted",
        "1 <= page_count <= 500",
    ]


def test_a_handle_that_cannot_be_read_is_not_blamed_on_the_document(tmp_path: Path) -> None:
    """A read error in our own temporary file is the server's fault. It surfaces as itself
    -- a 500 -- and not as an ``unparseable`` 422 sent to a caller whose PDF was fine."""
    path = _file_of(NAMED["ar_baseline.pdf"], tmp_path)

    class Failing(RecordingHandle):
        def readinto(self, buffer: Any) -> int:
            raise OSError("the disk went away")

    with path.open("rb") as inner:
        with pytest.raises(OSError):
            new_envelope.probe(Failing(inner), source_filename="a.pdf")  # type: ignore[arg-type]


def test_a_handle_that_cannot_seek_is_a_programming_error_not_a_refusal() -> None:
    class Stream(io.RawIOBase):
        def readable(self) -> bool:
            return True

        def readinto(self, buffer: Any) -> int:
            return 0

        def seekable(self) -> bool:
            return False

        def tell(self) -> int:
            return 0

        def seek(self, offset: int, whence: int = 0) -> int:
            raise io.UnsupportedOperation("seek")

    with pytest.raises(TypeError, match="seekable"):
        new_envelope.probe(Stream(), source_filename="a.pdf")  # type: ignore[arg-type]


@pytest.mark.parametrize("not_an_upload", ["a string", 42, None, object()])
def test_anything_that_is_neither_bytes_nor_a_handle_gets_the_old_refusal(
    not_an_upload: Any,
) -> None:
    expected = verdict(lambda: old_probe(not_an_upload, source_filename="a.pdf"))
    found = verdict(lambda: new_envelope.probe(not_an_upload, source_filename="a.pdf"))
    assert found == expected
    assert found[4] == {"field": "content", "constraint": "bytes"}


def test_the_comparison_is_made_against_the_pinned_parser() -> None:
    """The differential is only meaningful for the pypdfium2 the lock pins: a different one
    would be a different experiment, so a bump has to come here and re-run it."""
    from importlib.metadata import version

    assert version("pypdfium2") == "5.13.0"
