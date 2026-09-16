"""Every refusal the multipart reader can make, asserted on **which rule** refused.

`uploadDocument` is the only multipart operation in the frozen document, and the reader
is deliberately strict: a missing boundary, a part with no name, a repeated part and an
unknown part are each a refusal rather than a best guess. `W10-API` swept those refusals
by mutation and found that neutering the media-type check, the boundary check, the
part-name check and the repeated-part check each left all 816 tests green.

Two things every case below asserts, and the second is the one that matters:

* the reader refuses -- `DomainError(validation_failed)`;
* **`details["constraint"]`**, which names the rule. `details["field"]` cannot do that
  job here: `file` is the field for four different rules (`part_name`, `required`,
  `filename`, `max_bytes`) and `Content-Type` for two (`media_type`, `boundary`). A test
  asserting the field would pass whichever of them fired, which is exactly how a deleted
  check survives a sweep.

Bodies are built here, byte by byte. Nothing is read from `fixtures/synthetic/ar/**` or
`fixtures/validation/PC-02/**`: both are frozen evidence and adding to either would
invalidate a measurement already taken.
"""

from __future__ import annotations

import pytest

from auditmanager.api.routers.multipart import MultipartUpload, parse_multipart_upload
from auditmanager.shared.errors import DomainError, ErrorCode

BOUNDARY = "----w10apiboundary"
CONTENT_TYPE = f"multipart/form-data; boundary={BOUNDARY}"

#: `api/routers/multipart.py` declares `MAX_BODY = 26 * 1024 * 1024`. Written out rather
#: than imported. The existing `tests/integration/ingest/test_size_guard_boundary.py`
#: derives its payload size from `MAX_BODY` and `MAX_BYTES` together -- see the note in
#: the review -- so raising the transport limit does not redden it, it makes it allocate
#: a body proportional to the new limit. This number is the limit itself.
TRANSPORT_LIMIT = 27262976


def _body(*parts: tuple[str, bytes], headers: tuple[str, ...] = ()) -> bytes:
    """Frame parts into a multipart body. ``parts`` is (content-disposition, payload)."""
    out = b""
    for index, (disposition, payload) in enumerate(parts):
        extra = f"{headers[index]}\r\n" if index < len(headers) and headers[index] else ""
        out += f"--{BOUNDARY}\r\nContent-Disposition: {disposition}\r\n{extra}\r\n".encode()
        out += payload + b"\r\n"
    return out + f"--{BOUNDARY}--\r\n".encode()


FILE_PART = 'form-data; name="file"; filename="between.pdf"'


def _refusal(body: bytes, content_type: str | None = CONTENT_TYPE) -> DomainError:
    with pytest.raises(DomainError) as caught:
        parse_multipart_upload(body, content_type)
    return caught.value


class TestTheReaderAcceptsExactlyWhatTheSchemaDeclares:
    def test_a_file_part_alone_is_accepted(self) -> None:
        upload = parse_multipart_upload(_body((FILE_PART, b"%PDF-1.7\n")), CONTENT_TYPE)
        assert isinstance(upload, MultipartUpload)
        assert upload.content == b"%PDF-1.7\n"
        assert upload.filename == "between.pdf"
        assert upload.display_title is None

    def test_the_optional_display_title_is_read_as_utf8(self) -> None:
        upload = parse_multipart_upload(
            _body(
                (FILE_PART, b"%PDF-1.7\n"),
                ('form-data; name="display_title"', "Rapport trimestriel".encode("utf-8")),
            ),
            CONTENT_TYPE,
        )
        assert upload.display_title == "Rapport trimestriel"


class TestEachRefusalNamesItsOwnRule:
    """One case per refusing branch. The constraint string is the assertion."""

    def test_a_non_multipart_content_type_is_refused_as_media_type(self) -> None:
        error = _refusal(_body((FILE_PART, b"x")), "application/json")
        assert error.code is ErrorCode.VALIDATION_FAILED
        assert error.detail_fields["constraint"] == "media_type"

    def test_an_absent_content_type_is_refused_as_media_type(self) -> None:
        error = _refusal(_body((FILE_PART, b"x")), None)
        assert error.detail_fields["constraint"] == "media_type"

    def test_a_multipart_content_type_with_no_boundary_is_refused_as_boundary(self) -> None:
        """Distinct from ``media_type``: the media type is right and unreadable."""
        error = _refusal(_body((FILE_PART, b"x")), "multipart/form-data")
        assert error.detail_fields["constraint"] == "boundary"

    def test_a_part_with_no_name_is_refused_as_part_name(self) -> None:
        error = _refusal(_body(('form-data; filename="between.pdf"', b"x")))
        assert error.detail_fields["constraint"] == "part_name"

    def test_a_part_with_an_empty_name_is_refused_as_part_name(self) -> None:
        error = _refusal(_body(('form-data; name=""; filename="between.pdf"', b"x")))
        assert error.detail_fields["constraint"] == "part_name"

    def test_a_repeated_part_is_refused_as_unique_part(self) -> None:
        error = _refusal(
            _body(
                (FILE_PART, b"first"),
                ('form-data; name="file"; filename="second.pdf"', b"second"),
            )
        )
        assert error.detail_fields["constraint"] == "unique_part"

    def test_an_undeclared_part_is_refused_as_additional_properties(self) -> None:
        """`UploadDocumentRequest` is closed, for the same reason a JSON object is."""
        error = _refusal(
            _body((FILE_PART, b"x"), ('form-data; name="surprise"', b"y"))
        )
        assert error.detail_fields["constraint"] == "additionalProperties"

    def test_a_body_with_no_file_part_is_refused_as_required(self) -> None:
        error = _refusal(_body(('form-data; name="display_title"', b"Title")))
        assert error.detail_fields["constraint"] == "required"

    def test_a_file_part_with_no_filename_is_refused_as_filename(self) -> None:
        """Distinct from ``required``: the part is present and unnamed as a file."""
        error = _refusal(_body(('form-data; name="file"', b"x")))
        assert error.detail_fields["constraint"] == "filename"

    def test_a_file_part_with_an_empty_filename_is_refused_as_filename(self) -> None:
        error = _refusal(_body(('form-data; name="file"; filename=""', b"x")))
        assert error.detail_fields["constraint"] == "filename"

    def test_a_file_part_that_cannot_be_decoded_is_refused_as_encoding(self) -> None:
        """A part that is itself multipart decodes to ``None`` rather than to bytes.

        Reachable, and worth a test: without one the branch reads as defensive
        programming, and a reader that fell through it would hand ``None`` to the ingest
        command as a document body.
        """
        nested = (
            f"--{BOUNDARY}\r\n"
            'Content-Disposition: form-data; name="file"; filename="between.pdf"\r\n'
            "Content-Type: multipart/mixed; boundary=zz\r\n\r\n"
            "--zz\r\nContent-Type: text/plain\r\n\r\nhello\r\n--zz--\r\n"
            f"\r\n--{BOUNDARY}--\r\n"
        ).encode()
        error = _refusal(nested)
        assert error.detail_fields["field"] == "file"
        assert error.detail_fields["constraint"] == "encoding"

    def test_a_display_title_that_is_not_utf8_is_refused_as_encoding(self) -> None:
        error = _refusal(
            _body((FILE_PART, b"x"), ('form-data; name="display_title"', b"\xff\xfe\xfa"))
        )
        assert error.detail_fields["field"] == "display_title"
        assert error.detail_fields["constraint"] == "encoding"


class TestTheTransportBodyLimit:
    """`MAX_BODY` written as a literal, asserted at the boundary.

    26 MiB is the transport's own limit and no external authority declares it: the frozen
    OpenAPI document declares the *document* maximum, which is the envelope's 25 MiB
    `ENV-SIZE`, not this one. So the number is pinned here, which is what makes a drift in
    it a red test.
    """

    def test_the_limit_is_twenty_six_mebibytes(self) -> None:
        assert TRANSPORT_LIMIT == 26 * 1024 * 1024

    def test_a_body_one_byte_over_the_limit_is_refused_as_max_bytes(self) -> None:
        error = _refusal(b"x" * (TRANSPORT_LIMIT + 1))
        assert error.code is ErrorCode.VALIDATION_FAILED
        assert error.detail_fields["constraint"] == "max_bytes"

    def test_the_limit_is_checked_before_the_body_is_parsed(self) -> None:
        """An oversize body that is *also* unparseable answers ``max_bytes``.

        The order is the point: materialising an unbounded body to discover it has no
        boundary is the denial-of-service surface the limit exists to close.
        """
        error = _refusal(b"x" * (TRANSPORT_LIMIT + 1), "multipart/form-data")
        assert error.detail_fields["constraint"] == "max_bytes"


class TestARefusalNeverEchoesWhatTheCallerSent:
    """`B6`: an ``additionalProperties`` refusal that echoed the caller's own property
    name put a property named ``/etc/passwd`` inside the envelope. The reader's comments
    say part names and filenames are deliberately not echoed. Nothing checked it."""

    @pytest.mark.parametrize(
        ("label", "body", "secret"),
        [
            (
                "unknown_part_name",
                _body((FILE_PART, b"x"), ('form-data; name="/etc/passwd"', b"y")),
                "/etc/passwd",
            ),
            (
                "repeated_part_name",
                _body((FILE_PART, b"x"), ('form-data; name="file"; filename="b"', b"y")),
                "between.pdf",
            ),
        ],
        ids=["unknown_part_name", "repeated_part_name"],
    )
    def test_the_caller_s_own_text_is_absent_from_the_envelope(
        self, label: str, body: bytes, secret: str
    ) -> None:
        error = _refusal(body)
        rendered = str(error.envelope("cid-fixed-0001").as_dict())
        assert secret not in rendered, (
            f"{label}: the refusal reflected {secret!r} back to the caller"
        )
