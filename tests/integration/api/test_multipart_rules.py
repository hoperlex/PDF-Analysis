"""Every refusal the upload can make, asserted on **which rule** refused.

``uploadDocument`` is the only multipart operation in the frozen document, and the edge is
deliberately strict: an unreadable body, a part with no name, a repeated part and an
undeclared part are each a refusal rather than a best guess. `W10-API` swept those refusals
by mutation and found that neutering the media-type check, the boundary check, the
part-name check and the repeated-part check each left all 816 tests green.

Two things every case below asserts, and the second is the one that matters:

* the upload is refused -- ``422 validation_failed``;
* **``details.constraint``**, which names the rule. ``details.field`` cannot do that job
  here: ``file`` is the field for three different rules (``part_name``, ``required``,
  ``filename``), ``body`` for three (``unique_part``, ``additionalProperties``,
  ``readable_multipart``) and ``Content-Type`` for two (``media_type``, ``boundary``). A
  test asserting the field would pass whichever of them fired, which is exactly how a
  deleted check survives a sweep.

**Rewritten by `W13-API`, not re-pointed.** ``parse_multipart_upload`` and
``MultipartUpload`` are gone: FastAPI parses the body with ``python-multipart`` and the
closed ``UploadDocumentRequest`` model decides which parts are declared. So these cases
drive **the operation**, which is where the rules now live and is also the only place that
can show they are reached in the right order -- and the rewrite found two refusals the
framework was answering ``500 internal_error`` and one it was silently accepting:

* an absent ``boundary`` parameter and a part with no ``name`` both make Starlette raise
  ``MultiPartException``, which FastAPI turns into its own ``HTTPException(400)``. Neither
  reached a client as an envelope until ``BodyCapMiddleware`` and ``on_http_exception``
  were given the two cases below;
* ``FormData`` is a multidict and Pydantic reads the **last** value, so ``file`` sent twice
  was accepted and the second one published. ``require_a_strict_multipart_body`` refuses it.

**One vocabulary change, recorded rather than smuggled.** A part with an absent ``name``
answered ``constraint: "part_name"`` before this wave; it now answers
``"readable_multipart"``, because Starlette raises the same exception for four different
causes and this contract does not map refusals on another library's message text. A part
with an **empty** name still answers ``part_name``. No response-baseline record covers
either path. See ``docs/program/reviews/W13-API.md``.

Bodies are built here, byte by byte. Nothing is read from ``fixtures/synthetic/ar/**`` or
``fixtures/validation/PC-02/**``: both are frozen evidence and adding to either would
invalidate a measurement already taken.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from w13_api_driver import Request, Surface, dispatch

BOUNDARY = "----w10apiboundary"
CONTENT_TYPE = f"multipart/form-data; boundary={BOUNDARY}"

#: ``api/routers/multipart.py`` declares ``MAX_BODY = 26 * 1024 * 1024``. Written out
#: rather than imported: a test that reads the bound from the module it is checking cannot
#: tell you the bound moved. ``OPERATING_CONSTRAINTS.md`` section 12.
TRANSPORT_LIMIT = 27262976

#: Enough of a PDF that the refusals below are the transport's and not the envelope's. The
#: baseline document is not used: this file adds no bytes to any frozen corpus and needs
#: none, because every case here is refused before a byte reaches ``auditmanager.ingest``.
PDF = b"%PDF-1.7\n"

FILE_PART = 'form-data; name="file"; filename="between.pdf"'


def _body(*parts: tuple[str, bytes]) -> bytes:
    """Frame parts into a multipart body. ``parts`` is (content-disposition, payload)."""
    out = b""
    for disposition, payload in parts:
        out += f"--{BOUNDARY}\r\nContent-Disposition: {disposition}\r\n\r\n".encode()
        out += payload + b"\r\n"
    return out + f"--{BOUNDARY}--\r\n".encode()


@pytest.fixture
def project_uid(router: Surface) -> str:
    answer = dispatch(
        router,
        Request.build(
            "POST",
            "/projects",
            headers={"Content-Type": "application/json", "Idempotency-Key": "mp-project"},
            body=json.dumps({"name": "multipart rules"}).encode("utf-8"),
        ),
    )
    assert answer.status == 201, answer.body
    return json.loads(answer.body)["project_uid"]


_COUNTER = iter(range(1, 10_000))


def _upload(
    router: Surface,
    project_uid: str,
    body: bytes,
    content_type: str | None = CONTENT_TYPE,
) -> dict[str, Any]:
    """Drive one upload and return the parsed answer.

    A fresh ``Idempotency-Key`` per call, so no case can be answered by a replay of an
    earlier one -- which would make a refusal test pass for the wrong reason.
    """
    headers = {"Idempotency-Key": f"mp-{next(_COUNTER):04d}"}
    if content_type is not None:
        headers["Content-Type"] = content_type
    answer = dispatch(
        router,
        Request.build(
            "POST", f"/projects/{project_uid}/documents", headers=headers, body=body
        ),
    )
    return {"status": answer.status, "body": json.loads(answer.body)}


def _refusal(
    router: Surface,
    project_uid: str,
    body: bytes,
    content_type: str | None = CONTENT_TYPE,
) -> dict[str, Any]:
    answer = _upload(router, project_uid, body, content_type)
    assert answer["status"] == 422, answer
    assert answer["body"]["error_code"] == "validation_failed", answer
    return answer["body"]


class TestEachRefusalNamesItsOwnRule:
    """One case per refusing rule. The constraint string is the assertion."""

    def test_a_non_multipart_content_type_is_refused_as_media_type(
        self, router: Surface, project_uid: str
    ) -> None:
        body = _refusal(router, project_uid, _body((FILE_PART, PDF)), "application/json")
        assert body["details"] == {"field": "Content-Type", "constraint": "media_type"}

    def test_an_absent_content_type_is_refused_as_media_type(
        self, router: Surface, project_uid: str
    ) -> None:
        body = _refusal(router, project_uid, _body((FILE_PART, PDF)), None)
        assert body["details"] == {"field": "Content-Type", "constraint": "media_type"}

    def test_a_multipart_content_type_with_no_boundary_is_refused_as_boundary(
        self, router: Surface, project_uid: str
    ) -> None:
        """Distinct from ``media_type``: the media type is right and unreadable.

        Refused on the header, before any parser reads the body -- which is what
        ``BodyCapMiddleware`` is in front of the routing for. Answered ``500`` until it was.
        """
        body = _refusal(router, project_uid, _body((FILE_PART, PDF)), "multipart/form-data")
        assert body["details"] == {"field": "Content-Type", "constraint": "boundary"}
        assert body["message"] == (
            "The multipart body could not be read; the boundary may be missing."
        )

    def test_a_part_with_no_name_is_refused_as_an_unreadable_multipart(
        self, router: Surface, project_uid: str
    ) -> None:
        """Starlette's parser refuses this one, and FastAPI has already turned it into its
        own ``HTTPException(400)`` before any handler of this application could see it.
        What is asserted is that it still leaves as an envelope, and says the body is the
        thing that is wrong."""
        body = _refusal(
            router, project_uid, _body(('form-data; filename="between.pdf"', PDF))
        )
        assert body["details"] == {"field": "body", "constraint": "readable_multipart"}

    def test_a_part_with_an_empty_name_is_refused_as_part_name(
        self, router: Surface, project_uid: str
    ) -> None:
        """``name=""`` *parses*, so nothing in the framework objects: the part is simply
        not one the schema declares and the upload would look like one with no file."""
        body = _refusal(
            router, project_uid, _body(('form-data; name=""; filename="b.pdf"', PDF))
        )
        assert body["details"] == {"field": "file", "constraint": "part_name"}

    def test_a_repeated_part_is_refused_as_unique_part(
        self, router: Surface, project_uid: str
    ) -> None:
        """The one the framework accepted.

        ``FormData`` is a multidict; Pydantic sees the last value. Without this rule an
        upload carrying two ``file`` parts publishes the second and tells the caller
        nothing, which is precisely the "lenient multipart reader is a security surface"
        case the retired reader was strict about.
        """
        body = _refusal(
            router,
            project_uid,
            _body(
                (FILE_PART, PDF + b"first"),
                ('form-data; name="file"; filename="second.pdf"', PDF + b"second"),
            ),
        )
        assert body["details"] == {"field": "body", "constraint": "unique_part"}

    def test_an_undeclared_part_is_refused_as_additional_properties(
        self, router: Surface, project_uid: str
    ) -> None:
        """``UploadDocumentRequest`` is closed, for the same reason a JSON object is.

        ``records/26-uploadDocument.refusal.additionalProperties.json`` pins these bytes.
        """
        body = _refusal(
            router,
            project_uid,
            _body((FILE_PART, PDF), ('form-data; name="surprise"', b"y")),
        )
        assert body["details"] == {"field": "body", "constraint": "additionalProperties"}
        assert body["message"] == "The upload carries a part the schema does not declare."

    def test_a_body_with_no_file_part_is_refused_as_required(
        self, router: Surface, project_uid: str
    ) -> None:
        body = _refusal(
            router, project_uid, _body(('form-data; name="display_title"', b"Title"))
        )
        assert body["details"] == {"field": "file", "constraint": "required"}

    def test_a_file_part_with_no_filename_is_refused_as_filename(
        self, router: Surface, project_uid: str
    ) -> None:
        """Distinct from ``required``: the part is present and unnamed as a file.

        A part with no ``filename`` is not an upload to Starlette at all -- it is a text
        field -- so without this rule the caller is told their ``file`` is of the wrong
        *type*, which says nothing about what to fix.
        """
        body = _refusal(router, project_uid, _body(('form-data; name="file"', PDF)))
        assert body["details"] == {"field": "file", "constraint": "filename"}

    def test_a_file_part_with_an_empty_filename_is_refused_as_filename(
        self, router: Surface, project_uid: str
    ) -> None:
        body = _refusal(
            router, project_uid, _body(('form-data; name="file"; filename=""', PDF))
        )
        assert body["details"] == {"field": "file", "constraint": "filename"}

    def test_a_display_title_that_is_not_utf8_is_refused_as_encoding(
        self, router: Surface, project_uid: str
    ) -> None:
        """The certified reader did ``payload.decode("utf-8")``. Starlette does not.

        A part with no ``charset`` parameter is decoded latin-1 by
        ``starlette.formparsers._user_safe_decode``, so these three bytes arrive as three
        characters and nothing objects. ``require_a_strict_multipart_body`` restores the
        original bytes and decodes them as UTF-8 or refuses.
        """
        body = _refusal(
            router,
            project_uid,
            _body((FILE_PART, PDF), ('form-data; name="display_title"', b"\xff\xfe\xfa")),
        )
        assert body["details"] == {"field": "display_title", "constraint": "encoding"}

    def test_an_empty_display_title_is_refused_by_its_declared_bound(
        self, router: Surface, project_uid: str
    ) -> None:
        """``minLength: 1``. The model's own rule, reported as the model's own rule."""
        body = _refusal(
            router,
            project_uid,
            _body((FILE_PART, PDF), ('form-data; name="display_title"', b"")),
        )
        assert body["details"] == {"field": "display_title", "constraint": "length"}


class TestATitleTheCallerTypedArrivesAsTheCallerTypedIt:
    """The mojibake case, which is not a refusal and is the reason the rule above exists.

    ``agent/display-title`` is a fix already made once in this programme for the same
    property: *the display title reaches the reviewer who typed it*. Starlette's latin-1
    fallback would have undone it for every title with a character outside ASCII, silently
    -- no refusal, no log, just a wrong string in the database.
    """

    def test_a_utf8_title_survives_the_round_trip(
        self, router: Surface, project_uid: str
    ) -> None:
        title = "Rapport trimestriel — coûts & délais"
        answer = _upload(
            router,
            project_uid,
            _body(
                (FILE_PART, PDF),
                ('form-data; name="display_title"', title.encode("utf-8")),
            ),
        )
        # The upload is refused by the *envelope* -- these nine bytes are not a PDF the
        # extractor can read -- and that is far enough: what is asserted is that the title
        # was not the thing refused, and that no mojibake reached a refusal about it.
        assert answer["status"] == 422, answer
        assert answer["body"]["details"].get("field") != "display_title", answer
        assert "Ã" not in json.dumps(answer["body"]), answer


class TestTheTransportBodyLimit:
    """``MAX_BODY`` written as a literal, asserted at the boundary.

    26 MiB is the transport's own limit and no external authority declares it: the frozen
    OpenAPI document declares the *document* maximum, which is the envelope's 25 MiB
    ``ENV-SIZE``, not this one. So the number is pinned here, which is what makes a drift
    in it a red test.
    """

    def test_the_limit_is_twenty_six_mebibytes(self) -> None:
        assert TRANSPORT_LIMIT == 26 * 1024 * 1024

    def test_a_body_one_byte_over_the_limit_is_refused_as_max_bytes(
        self, router: Surface, project_uid: str
    ) -> None:
        """``records/22-uploadDocument.refusal.max_bytes.json`` pins these bytes."""
        body = _refusal(router, project_uid, b"x" * (TRANSPORT_LIMIT + 1))
        assert body["details"] == {"field": "file", "constraint": "max_bytes"}
        assert body["message"] == "The upload exceeds the maximum accepted size."

    def test_the_limit_is_checked_before_the_body_is_parsed(
        self, router: Surface, project_uid: str
    ) -> None:
        """An oversize body that is *also* unparseable answers ``max_bytes``.

        The order is the point: materialising an unbounded body to discover it has no
        boundary is the denial-of-service surface the limit exists to close. It is also why
        the limit is a middleware and not a dependency -- FastAPI parses a form before it
        resolves dependencies.
        """
        body = _refusal(
            router, project_uid, b"x" * (TRANSPORT_LIMIT + 1), "multipart/form-data"
        )
        assert body["details"] == {"field": "file", "constraint": "max_bytes"}


class TestARefusalNeverEchoesWhatTheCallerSent:
    """`B6`: an ``additionalProperties`` refusal that echoed the caller's own property name
    put a property named ``/etc/passwd`` inside the envelope. The comments said part names
    and filenames are deliberately not echoed. Nothing checked it."""

    @pytest.mark.parametrize(
        ("label", "parts", "secret"),
        [
            (
                "unknown_part_name",
                ((FILE_PART, PDF), ('form-data; name="/etc/passwd"', b"y")),
                "/etc/passwd",
            ),
            (
                "repeated_part_name",
                (
                    (FILE_PART, PDF),
                    ('form-data; name="file"; filename="/var/lib/secret.key"', b"y"),
                ),
                "secret.key",
            ),
        ],
        ids=["unknown_part_name", "repeated_part_name"],
    )
    def test_the_callers_own_text_is_absent_from_the_envelope(
        self,
        router: Surface,
        project_uid: str,
        label: str,
        parts: tuple[tuple[str, bytes], ...],
        secret: str,
    ) -> None:
        body = _refusal(router, project_uid, _body(*parts))
        assert secret not in json.dumps(body), (
            f"{label}: the refusal reflected {secret!r} back to the caller"
        )
