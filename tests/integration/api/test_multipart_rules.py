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

**One refusal is not reproduced, and it has a test of its own rather than a sentence.** A
``display_title`` whose bytes are not valid UTF-8 was refused before this wave and is
accepted now: see
``test_a_display_title_that_is_not_utf8_is_accepted_and_that_is_declared`` and
``_decoded_title``.

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

**`W55B-STREAM-01` added the transport's other half**, in the two classes at the end of this
file: the body cap is per route (``uploadDocument`` takes 251 MiB, every other route keeps
26 MiB) and at most two uploads are in flight in one API process, the third refused before
its body is read. Those classes need no database -- they drive ``BodyCapMiddleware`` and the
documentation application directly -- and say what each of the guard's three exits (finish,
failure, cancellation, disconnect) does to the gate.

Bodies are built here, byte by byte. Nothing is read from ``fixtures/synthetic/ar/**`` or
``fixtures/validation/PC-02/**``: both are frozen evidence and adding to either would
invalidate a measurement already taken.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

import pytest
from fastapi import FastAPI, File, UploadFile
from starlette.requests import ClientDisconnect
from starlette.testclient import TestClient

from w13_api_driver import Request, Surface, dispatch

BOUNDARY = "----w10apiboundary"
CONTENT_TYPE = f"multipart/form-data; boundary={BOUNDARY}"

#: ``api/routers/multipart.py`` declares ``MAX_BODY = 26 * 1024 * 1024``, the cap of every
#: route that is not an upload. Written out rather than imported: a test that reads the
#: bound from the module it is checking cannot tell you the bound moved.
#: ``OPERATING_CONSTRAINTS.md`` section 12.
TRANSPORT_LIMIT = 27262976

#: ``UPLOAD_MAX_BODY = 251 * 1024 * 1024``, the cap of ``uploadDocument`` alone
#: (`W55B-STREAM-01`): a 250 MiB bundle and the multipart framing around it.
UPLOAD_LIMIT = 263192576

#: Enough of a PDF that the refusals below are the transport's and not the envelope's. The
#: baseline document is not used: this file adds no bytes to any frozen corpus and needs
#: none, because every case here is refused before a byte reaches ``auditmanager.ingest``.
PDF = b"%PDF-1.7\n"
#: `W55B-INGEST-01`: the first bytes of an upload that is a ZIP -- what the envelope reads.
ZIP = b"PK\x03\x04"

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

    def test_a_bare_pdf_is_refused_as_portal_bundle_required_and_publishes_nothing(
        self, router: Surface, project_uid: str, corpus_pdf: bytes
    ) -> None:
        """`W55B-INGEST-01`, last step: the committed baseline PDF -- a real, valid document --
        sent as the ``file`` part through the route is refused, with the registered
        constraint, ``field: file`` and the Russian sentence on how to obtain the bundle.

        Whatever its label (``application/pdf`` here) and whatever its name (``.pdf``): a
        ZIP is recognised by its first bytes alone. Nothing is published, which is read back
        through the route rather than assumed from the status.
        """
        body = _refusal(router, project_uid, _body((FILE_PART, corpus_pdf)))
        assert body["details"] == {"field": "file", "constraint": "portal_bundle_required"}
        assert body["message"].startswith("Загрузите комплект портала распознавания")
        assert "Отдельный PDF не принимается" in body["message"]
        listed = dispatch(router, Request.build("GET", f"/projects/{project_uid}/documents"))
        assert listed.status == 200, listed.body
        assert json.loads(listed.body)["items"] == []

    def test_a_display_title_that_is_not_utf8_is_accepted_and_that_is_declared(
        self, router: Surface, project_uid: str, corpus_bundle: bytes
    ) -> None:
        """**The one refusal of the retired reader this transport does not reproduce.**

        It did ``payload.decode("utf-8")`` and raised ``display_title`` / ``encoding``.
        Starlette never refuses a text part: invalid UTF-8 falls back to latin-1 and comes
        back as a string, and the fallback is *indistinguishable* from a correctly decoded
        title of Latin-1-range characters -- see ``_decoded_title`` for the two byte
        sequences that give the same string. Refusing on that test refuses ``"coûts"``,
        which the case below requires to be accepted.

        This test exists so the change is **met** by a reader rather than trusted from
        prose, which is the pattern `W13-CONF` used for its own declared blind spot. No
        response-baseline record covers this path. Reported in
        ``docs/program/reviews/W13-API.md``.
        """
        answer = _upload(
            router,
            project_uid,
            _body(
                (FILE_PART, corpus_bundle),
                ('form-data; name="display_title"', b"\xff\xfe\xfa"),
            ),
        )
        assert answer["status"] == 201, answer

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
    """The other side of the encoding rule: a good title must not be refused or rewritten.

    ``agent/display-title`` is a fix already made once in this programme for the same
    property: *the display title reaches the reviewer who typed it*. Two titles, and the
    second is the one that matters:

    * one with a character outside latin-1 (an em dash), which cannot have come from
      Starlette's fallback and is passed through;
    * one made **only of Latin-1-range characters** -- ``coûts`` -- which is exactly the
      shape a naive recovery destroys. An earlier version of ``_decoded_title``
      re-encoded latin-1 and decoded UTF-8 unconditionally, so ``"coûts"`` became
      ``b"co\xfbts"``, which is not valid UTF-8, and a perfectly good title was **refused**.
      No test in this file reddened for it. This one does.
    """

    def test_a_utf8_title_survives_the_round_trip(
        self, router: Surface, project_uid: str, corpus_bundle: bytes, session
    ) -> None:
        """A real published version, and the title read back out of the row that holds it.

        Asserted against **storage**, not against a refusal. The failure this guards
        against is silent -- no refusal, no log, a wrong string in the database -- and the
        title sits on ``document``, not on ``DocumentVersion``, so no response on this
        surface would show it. A test that stopped at the 201 could not see the defect at
        all. ``corpus_bundle`` is the AR baseline bundle the rest of this suite publishes;
        nothing is added to any frozen corpus.
        """
        from sqlalchemy import text

        title = "Rapport trimestriel — coûts & délais"
        answer = _upload(
            router,
            project_uid,
            _body(
                (FILE_PART, corpus_bundle),
                ('form-data; name="display_title"', title.encode("utf-8")),
            ),
        )
        assert answer["status"] == 201, answer
        stored = session.execute(
            text("SELECT display_title FROM document WHERE document_uid = :uid"),
            {"uid": answer["body"]["document_uid"]},
        ).scalar_one()
        assert stored == title, (
            f"the title the reviewer typed did not survive the transport: {stored!r}"
        )

    def test_a_title_made_only_of_latin1_characters_is_accepted(
        self, router: Surface, project_uid: str, corpus_bundle: bytes, session
    ) -> None:
        """``coûts`` -- every character under U+0100, and valid UTF-8 on the wire.

        This is the case a recovery that *rewrites* destroys, and the case that has to be
        told apart from a genuine latin-1 fallback. The discriminator is not the string:
        it is that Starlette only falls back when the bytes are not valid UTF-8, so bytes
        that decode are bytes it already decoded.
        """
        from sqlalchemy import text

        title = "coûts et délais"
        answer = _upload(
            router,
            project_uid,
            _body(
                (FILE_PART, corpus_bundle),
                ('form-data; name="display_title"', title.encode("utf-8")),
            ),
        )
        assert answer["status"] == 201, answer
        stored = session.execute(
            text("SELECT display_title FROM document WHERE document_uid = :uid"),
            {"uid": answer["body"]["document_uid"]},
        ).scalar_one()
        assert stored == title, (
            f"a valid UTF-8 title of Latin-1-range characters was not stored as typed: "
            f"{stored!r}"
        )


def _framed(total: int, head: bytes = PDF) -> bytes:
    """A multipart body of exactly ``total`` bytes whose file part is ``head`` and padding.

    The same construction ``characterization/w13_baseline/journey.sized_multipart`` uses for
    records 18 and 22: the padding is the point, so a body can reach any size without a
    fixture being added to a frozen corpus.
    """
    frame = len(_body((FILE_PART, b"")))
    payload = head + b"0" * (total - frame - len(head))
    body = _body((FILE_PART, payload))
    assert len(body) == total, (len(body), total)
    return body


class TestTheTransportBodyLimit:
    """The two caps written as literals, asserted at their boundaries.

    26 MiB is the limit of every route that is not an upload and 251 MiB the upload route's;
    no external authority declares either: the frozen OpenAPI document declares the
    *document* maximum, which is the envelope's 250 MiB ``ENV-SIZE``, not these. So the
    numbers are pinned here, which is what makes a drift in them a red test.
    """

    def test_the_limit_of_every_other_route_is_twenty_six_mebibytes(self) -> None:
        assert TRANSPORT_LIMIT == 26 * 1024 * 1024

    def test_the_limit_of_the_upload_route_is_two_hundred_and_fifty_one_mebibytes(self) -> None:
        """A 250 MiB bundle and a mebibyte for the framing around it."""
        assert UPLOAD_LIMIT == 251 * 1024 * 1024

    def test_the_module_declares_the_numbers_this_file_writes_out(self) -> None:
        from auditmanager.api.routers.multipart import MAX_BODY, UPLOAD_MAX_BODY

        assert (MAX_BODY, UPLOAD_MAX_BODY) == (TRANSPORT_LIMIT, UPLOAD_LIMIT)

    def test_a_body_one_byte_over_the_limit_of_an_ordinary_route_is_refused_as_max_bytes(
        self, router: Surface
    ) -> None:
        """The bytes ``records/22-uploadDocument.refusal.max_bytes.json`` pins, on the routes
        that still have this limit: the answer is the one an upload used to get at 26 MiB."""
        answer = dispatch(
            router,
            Request.build(
                "POST",
                "/projects",
                headers={"Content-Type": CONTENT_TYPE, "Idempotency-Key": "mp-ordinary"},
                body=b"x" * (TRANSPORT_LIMIT + 1),
            ),
        )
        body = json.loads(answer.body)
        assert answer.status == 422, body
        assert body["details"] == {"field": "file", "constraint": "max_bytes"}
        assert body["message"] == "The upload exceeds the maximum accepted size."

    def test_the_body_that_used_to_be_refused_at_the_upload_route_now_reaches_the_envelope(
        self, router: Surface, project_uid: str
    ) -> None:
        """The same 26 MiB-and-one-byte body, framed, sent to ``uploadDocument``.

        Until `W55B-STREAM-01` this was ``max_bytes`` (record 22). The upload route's cap is
        251 MiB, so the transport lets it through and the envelope is the guard that speaks.
        Since `W55B-INGEST-01` the envelope's bound is 250 MiB and this body is far inside
        it: what the envelope answers is about what the body *holds* -- a ZIP header and
        zeros, an archive it cannot read -- and never about its size.
        """
        body = _refusal(router, project_uid, _framed(TRANSPORT_LIMIT + 1, ZIP))
        assert body["details"] == {"field": "file", "constraint": "bundle_unreadable"}
        assert body["message"] == "The archive could not be read as a ZIP file."

    def test_the_limit_is_checked_before_the_body_is_parsed(self, router: Surface) -> None:
        """An oversize body that is *also* unparseable answers ``max_bytes``.

        The order is the point: materialising an unbounded body to discover it has no
        boundary is the denial-of-service surface the limit exists to close. It is also why
        the limit is a middleware and not a dependency -- FastAPI parses a form before it
        resolves dependencies.
        """
        answer = dispatch(
            router,
            Request.build(
                "POST",
                "/projects",
                headers={"Content-Type": "multipart/form-data", "Idempotency-Key": "mp-order"},
                body=b"x" * (TRANSPORT_LIMIT + 1),
            ),
        )
        body = json.loads(answer.body)
        assert answer.status == 422, body
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


# ---------------------------------------------------------------------------------------
# `W55B-STREAM-01`: the upload gate and the per-route caps. No database, no object store.
# ---------------------------------------------------------------------------------------

UPLOAD_PATH = "/projects/prj_01ARZ3NDEKTSV4RRFFQ69G5FAV/documents"
OTHER_PATH = "/projects"
MULTIPART = f"multipart/form-data; boundary={BOUNDARY}".encode()
JSON_TYPE = b"application/json"
#: The credential the stand-in check of these middleware tests accepts (`W55B-FIX`, X-3: the
#: upload route needs one before its slot). The real check is ``build_credential_precheck``.
GOOD_TOKEN = "good-credential"


def _accepts_good(token: str) -> bool:
    return token == GOOD_TOKEN


@dataclass
class Exchange:
    """What one request through the middleware looked like from both ends."""

    status: int | None = None
    headers: list[tuple[str, str]] = field(default_factory=list)
    body: bytes = b""
    receives: int = 0
    delivered: int = 0

    @property
    def envelope(self) -> dict[str, Any]:
        return json.loads(self.body)


async def drive(
    app: Any,
    *,
    path: str = UPLOAD_PATH,
    method: str = "POST",
    content_type: bytes | None = MULTIPART,
    declared: int | None = None,
    chunks: tuple[bytes, ...] = (b"x",),
    until_disconnect: asyncio.Event | None = None,
    authorization: bytes | None = b"Bearer " + GOOD_TOKEN.encode(),
) -> Exchange:
    """Send one request into an ASGI app and keep both sides of the conversation.

    With ``until_disconnect`` the body never ends: once the chunks are delivered ``receive``
    waits for the event and then reports the client gone, which is a client that stops
    sending in the middle of an upload.
    """
    exchange = Exchange()
    pending = list(chunks)
    headers: list[tuple[bytes, bytes]] = []
    if content_type is not None:
        headers.append((b"content-type", content_type))
    if declared is not None:
        headers.append((b"content-length", str(declared).encode()))
    if authorization is not None:
        headers.append((b"authorization", authorization))

    async def receive() -> dict[str, Any]:
        exchange.receives += 1
        if pending:
            chunk = pending.pop(0)
            exchange.delivered += len(chunk)
            return {"type": "http.request", "body": chunk, "more_body": True}
        if until_disconnect is not None:
            await until_disconnect.wait()
        return {"type": "http.disconnect"}

    async def send(message: dict[str, Any]) -> None:
        if message["type"] == "http.response.start":
            exchange.status = message["status"]
            exchange.headers = [(k.decode("latin-1"), v.decode("latin-1")) for k, v in message["headers"]]
        elif message["type"] == "http.response.body":
            exchange.body += message.get("body", b"")

    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "root_path": "",
        "headers": headers,
        "query_string": b"",
    }
    await app(scope, receive, send)
    return exchange


class HoldingApp:
    """An application that takes its time: it waits to be released and then answers ``204``.

    ``mode`` chooses how a request leaves it -- the four ways a slot has to be given back.
    """

    def __init__(self) -> None:
        self.entered = 0
        self.left = 0
        self.release = asyncio.Event()
        self.mode = "finish"

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        self.entered += 1
        try:
            if self.mode == "disconnect":
                # Reads the body as a form parser does, and stops when the client goes.
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        raise ClientDisconnect()
            await self.release.wait()
            if self.mode == "fail":
                raise RuntimeError("the handler failed")
            await send({"type": "http.response.start", "status": 204, "headers": []})
            await send({"type": "http.response.body", "body": b""})
        finally:
            self.left += 1


def stack(inner: Any, **options: Any) -> Any:
    """The two outer layers the application puts around the gate, and nothing else."""
    from auditmanager.api.routers.correlation import CorrelationMiddleware
    from auditmanager.api.routers.multipart import BodyCapMiddleware

    options.setdefault("verify_credential", _accepts_good)
    gate = BodyCapMiddleware(inner, **options)
    return CorrelationMiddleware(gate), gate


def run(scenario: Awaitable[Any], seconds: float = 20.0) -> Any:
    """Run a scenario to the end or fail it.

    A gate that stopped refusing leaves a request waiting for a release the scenario would
    only give afterwards, and that would hang the suite instead of failing the test. The
    deadline turns the hang into the failure it is.
    """
    return asyncio.run(asyncio.wait_for(scenario, seconds))


async def until(condition: Callable[[], bool], what: str) -> None:
    for _ in range(2000):
        if condition():
            return
        await asyncio.sleep(0.001)
    raise AssertionError(f"timed out waiting for {what}")


class TestTheUploadGate:
    """At most two uploads in flight; the third is refused before its body is read."""

    def test_the_third_upload_is_refused_before_its_body_is_read(self) -> None:
        async def scenario() -> None:
            inner = HoldingApp()
            app, gate = stack(inner)
            first = asyncio.create_task(drive(app))
            second = asyncio.create_task(drive(app))
            await until(lambda: inner.entered == 2, "two uploads inside the application")

            third = await drive(app, chunks=(b"y" * 1000,))

            assert third.status == 503
            assert third.envelope["error_code"] == "dependency_unavailable"
            assert third.envelope["details"] == {"dependency": "upload_capacity"}
            assert third.envelope["retryable"] is True
            assert third.receives == 0, "the refused upload's body was touched"
            assert third.delivered == 0
            assert inner.entered == 2, "the refused upload reached the application"
            assert gate.gate.in_flight == 2

            inner.release.set()
            assert [(await first).status, (await second).status] == [204, 204]
            assert gate.gate.in_flight == 0

        run(scenario())

    def test_the_refusal_carries_retry_after_between_the_length_and_the_correlation_id(
        self,
    ) -> None:
        async def scenario() -> None:
            inner = HoldingApp()
            app, _ = stack(inner)
            held = [asyncio.create_task(drive(app)) for _ in range(2)]
            await until(lambda: inner.entered == 2, "two uploads inside the application")

            refused = await drive(app)

            assert [name for name, _ in refused.headers] == [
                "Content-Type",
                "Content-Length",
                "Retry-After",
                "X-Correlation-Id",
            ], refused.headers
            values = dict(refused.headers)
            assert values["Content-Type"] == "application/json"
            assert values["Retry-After"] == "5"
            assert values["Content-Length"] == str(len(refused.body))
            inner.release.set()
            await asyncio.gather(*held)

        run(scenario())

    @pytest.mark.parametrize("mode", ["finish", "fail", "cancel", "disconnect"])
    def test_a_slot_comes_back_however_the_request_ends(self, mode: str) -> None:
        """Finished, failed, cancelled, disconnected: each leaves the gate whole.

        After the request ends the gate must hold nothing, and must still admit exactly two
        -- a slot lost to a leak would show as a second, smaller capacity.
        """

        async def scenario() -> None:
            inner = HoldingApp()
            app, gate = stack(inner)
            inner.mode = "fail" if mode == "fail" else ("disconnect" if mode == "disconnect" else "finish")

            pull_the_plug = asyncio.Event()
            doomed = asyncio.create_task(
                drive(app, chunks=(b"x",), until_disconnect=pull_the_plug)
            )
            await until(lambda: inner.entered == 1, "the request inside the application")
            assert gate.gate.in_flight == 1
            if mode == "cancel":
                doomed.cancel()
            elif mode == "disconnect":
                pull_the_plug.set()
            else:
                inner.release.set()
            try:
                await doomed
            except (asyncio.CancelledError, RuntimeError, ClientDisconnect):
                pass
            await until(lambda: inner.left == 1, "the request to leave the application")

            assert gate.gate.in_flight == 0, f"a request that {mode} kept its slot"

            # Whole capacity again: two in, the third out.
            inner.mode = "finish"
            inner.release = asyncio.Event()
            held = [asyncio.create_task(drive(app)) for _ in range(2)]
            await until(lambda: inner.entered == 3, "two more uploads inside the application")
            assert (await drive(app)).status == 503
            inner.release.set()
            await asyncio.gather(*held)
            assert gate.gate.in_flight == 0

        run(scenario())

    def test_only_an_upload_takes_a_slot(self) -> None:
        """The gate counts ``POST`` of the upload route. Nothing else waits behind it."""

        async def scenario() -> None:
            inner = HoldingApp()
            app, _ = stack(inner)
            held = [asyncio.create_task(drive(app)) for _ in range(2)]
            await until(lambda: inner.entered == 2, "two uploads inside the application")
            inner.release.set()  # everything else answers at once

            for label, kwargs in {
                "another route": {"path": OTHER_PATH},
                "listing the same collection": {"method": "GET", "path": UPLOAD_PATH, "content_type": None},
                "a longer path": {"path": UPLOAD_PATH + "/extra"},
                "another method": {"method": "PUT"},
            }.items():
                answer = await drive(app, **kwargs)
                assert answer.status == 204, f"{label} was refused as busy: {answer.status}"
            await asyncio.gather(*held)

        run(scenario())

    @pytest.mark.parametrize(
        ("label", "kwargs", "constraint"),
        [
            ("declared over the cap", {"declared": UPLOAD_LIMIT + 1}, "max_bytes"),
            ("multipart with no boundary", {"content_type": b"multipart/form-data"}, "boundary"),
        ],
    )
    def test_a_refusal_no_retry_could_cure_is_not_reported_as_busy(
        self, label: str, kwargs: dict[str, Any], constraint: str
    ) -> None:
        async def scenario() -> None:
            inner = HoldingApp()
            app, _ = stack(inner)
            held = [asyncio.create_task(drive(app)) for _ in range(2)]
            await until(lambda: inner.entered == 2, "two uploads inside the application")

            answer = await drive(app, **kwargs)

            assert answer.status == 422, f"{label}: {answer.status}"
            assert answer.envelope["details"]["constraint"] == constraint
            assert answer.receives == 0
            assert "Retry-After" not in dict(answer.headers)
            inner.release.set()
            await asyncio.gather(*held)

        run(scenario())

    def test_the_capacity_is_the_gates_and_not_a_constant_of_two(self) -> None:
        async def scenario() -> None:
            inner = HoldingApp()
            app, gate = stack(inner, max_concurrent_uploads=1)
            held = asyncio.create_task(drive(app))
            await until(lambda: inner.entered == 1, "one upload inside the application")
            assert (await drive(app)).status == 503
            inner.release.set()
            await held
            assert gate.gate.in_flight == 0

        run(scenario())

    def test_the_assembled_application_admits_two_and_caps_each_route(self) -> None:
        """The numbers the application is wired with, read off its middleware stack."""
        from auditmanager.api.app import create_documentation_app
        from auditmanager.api.routers.multipart import BodyCapMiddleware

        wired = [m for m in create_documentation_app().user_middleware if m.cls is BodyCapMiddleware]
        assert len(wired) == 1
        kwargs = dict(wired[0].kwargs)
        verify = kwargs.pop("verify_credential")
        assert kwargs == {
            "limit": TRANSPORT_LIMIT,
            "upload_limit": UPLOAD_LIMIT,
            "max_concurrent_uploads": 2,
        }
        # `W55B-FIX` (X-3): the documentation application has no deployment secret, so its
        # front door admits nobody -- the seam's own rule.
        assert callable(verify) and verify("am2.anything.at-all") is False


class ConsumingApp:
    """An application that reads its whole body and answers ``204``."""

    def __init__(self) -> None:
        self.read = 0

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        while True:
            message = await receive()
            if message["type"] != "http.request":
                break
            self.read += len(message["body"])
            if not message.get("more_body"):
                break
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})


class TestEveryRouteHasItsOwnCap:
    """The upload route takes 251 MiB; every other route keeps 26 MiB, exactly as before."""

    @pytest.mark.parametrize(
        ("path", "declared", "admitted"),
        [
            (UPLOAD_PATH, UPLOAD_LIMIT, True),
            (UPLOAD_PATH, UPLOAD_LIMIT + 1, False),
            (UPLOAD_PATH, TRANSPORT_LIMIT + 1, True),
            (OTHER_PATH, TRANSPORT_LIMIT, True),
            (OTHER_PATH, TRANSPORT_LIMIT + 1, False),
            (OTHER_PATH, UPLOAD_LIMIT, False),
            ("/runs", TRANSPORT_LIMIT + 1, False),
            (UPLOAD_PATH + "/", TRANSPORT_LIMIT + 1, False),
        ],
    )
    def test_the_declared_length_is_judged_against_the_cap_of_the_route(
        self, path: str, declared: int, admitted: bool
    ) -> None:
        async def scenario() -> Exchange:
            app, _ = stack(ConsumingApp())
            return await drive(app, path=path, declared=declared)

        answer = run(scenario())
        if admitted:
            assert answer.status == 204, answer.body
        else:
            assert answer.status == 422
            assert answer.envelope["details"] == {"field": "file", "constraint": "max_bytes"}
            assert answer.receives == 0, "an oversize body was read to discover it was oversize"

    def test_a_json_body_to_an_ordinary_route_is_refused_with_the_body_wording(self) -> None:
        async def scenario() -> Exchange:
            app, _ = stack(ConsumingApp())
            return await drive(
                app, path=OTHER_PATH, content_type=JSON_TYPE, declared=TRANSPORT_LIMIT + 1
            )

        answer = run(scenario())
        assert answer.status == 422
        assert answer.envelope["details"] == {"field": "body", "constraint": "max_bytes"}
        assert answer.envelope["message"] == "The request body exceeds the maximum accepted size."

    @pytest.mark.parametrize(
        ("path", "limit", "upload_limit", "refused"),
        [(OTHER_PATH, 1000, 5000, True), (UPLOAD_PATH, 1000, 5000, False)],
    )
    def test_a_body_with_no_declared_length_is_counted_against_the_same_cap(
        self, path: str, limit: int, upload_limit: int, refused: bool
    ) -> None:
        """Every body the web tier streams has no ``Content-Length``: the count is the guard."""

        async def scenario() -> tuple[Exchange, ConsumingApp]:
            inner = ConsumingApp()
            app, _ = stack(inner, limit=limit, upload_limit=upload_limit)
            return await drive(app, path=path, chunks=(b"y" * 400,) * 3), inner  # 1200 bytes

        answer, inner = run(scenario())
        if refused:
            assert answer.status == 422
            assert answer.envelope["details"] == {"field": "file", "constraint": "max_bytes"}
            assert inner.read <= 800, "the body kept being read after it passed the cap"
        else:
            assert answer.status == 204

    def test_the_count_stops_a_body_past_the_upload_cap_too(self) -> None:
        async def scenario() -> tuple[Exchange, ConsumingApp]:
            inner = ConsumingApp()
            app, _ = stack(inner, limit=1000, upload_limit=5000)
            return await drive(app, chunks=(b"y" * 1000,) * 8), inner

        answer, inner = run(scenario())
        assert answer.status == 422
        assert answer.envelope["details"] == {"field": "file", "constraint": "max_bytes"}
        assert inner.read <= 5000

    def test_the_cap_wins_over_the_framework_when_it_turns_the_failure_into_its_own(self) -> None:
        """FastAPI answers an exception raised while it reads a form with its own 400, which
        the application renders as ``readable_multipart``. A body passed the cap, so the cap
        speaks -- the same ``max_bytes`` a declared length gets."""
        from auditmanager.api.routers import install_exception_handlers
        from auditmanager.api.routers.correlation import CorrelationMiddleware
        from auditmanager.api.routers.multipart import BodyCapMiddleware

        app = FastAPI()

        @app.post("/projects/{project_uid}/documents")
        def upload(project_uid: str, file: UploadFile = File(...)) -> dict[str, int]:
            return {"bytes": len(file.file.read())}

        install_exception_handlers(app)
        app.add_middleware(
            BodyCapMiddleware, limit=1000, upload_limit=5000, verify_credential=_accepts_good
        )
        app.add_middleware(CorrelationMiddleware)

        def chunked(size: int) -> Any:
            yield f'--{BOUNDARY}\r\nContent-Disposition: {FILE_PART}\r\n\r\n'.encode()
            for _ in range(size // 500):
                yield b"y" * 500
            yield f"\r\n--{BOUNDARY}--\r\n".encode()

        client = TestClient(app, raise_server_exceptions=False)
        headers = {"Content-Type": CONTENT_TYPE, "Authorization": f"Bearer {GOOD_TOKEN}"}
        within = client.post(UPLOAD_PATH, headers=headers, content=chunked(4000))
        over = client.post(UPLOAD_PATH, headers=headers, content=chunked(6000))

        assert within.status_code == 200, within.text
        assert over.status_code == 422, over.text
        assert json.loads(over.content)["details"] == {"field": "file", "constraint": "max_bytes"}


class TestTheRealApplicationKeepsEachCap:
    """The assembled application, without a database: nothing is behind its ports, which is
    enough, because every case here is answered by the transport or the seam."""

    @staticmethod
    def client() -> Any:
        from auditmanager.api.app import create_documentation_app

        return TestClient(create_documentation_app(), raise_server_exceptions=False)

    def test_a_twenty_seven_mebibyte_json_body_to_another_route_is_refused_as_max_bytes(self) -> None:
        response = self.client().post(
            "/projects",
            headers={"Content-Type": "application/json", "Idempotency-Key": "mp-json-0001"},
            content=b'{"name": "' + b"x" * TRANSPORT_LIMIT + b'"}',
        )
        assert response.status_code == 422
        body = json.loads(response.content)
        assert body["details"] == {"field": "body", "constraint": "max_bytes"}
        assert body["message"] == "The request body exceeds the maximum accepted size."

    def test_the_same_size_of_multipart_to_another_route_gets_record_22s_words(self) -> None:
        response = self.client().post(
            "/projects",
            headers={"Content-Type": CONTENT_TYPE, "Idempotency-Key": "mp-multipart-0001"},
            content=_framed(TRANSPORT_LIMIT + 1),
        )
        assert response.status_code == 422
        body = json.loads(response.content)
        assert body["details"] == {"field": "file", "constraint": "max_bytes"}
        assert body["message"] == "The upload exceeds the maximum accepted size."

    def test_the_upload_route_lets_that_size_through_to_the_seam(self) -> None:
        """Past the old cap, under the new: the transport admits it, and the next layer --
        here the seam, which has no credential port -- is the one that answers."""
        response = self.client().post(
            UPLOAD_PATH,
            headers={
                "Content-Type": CONTENT_TYPE,
                "Idempotency-Key": "mp-upload-0001",
                "Authorization": "Bearer anything",
            },
            content=_framed(TRANSPORT_LIMIT + 1),
        )
        body = json.loads(response.content)
        assert body.get("details", {}).get("constraint") != "max_bytes", body
        assert response.status_code == 401, body


class TestTheUploadRouteHasAFrontDoor:
    """`W55B-FIX` (X-3; `W55B-QA-01` QA-1). FastAPI parses a form before it solves the seam, so
    a caller with no credential had its body read and spooled, holding an upload slot, before
    the ``401``; two such callers kept every upload busy. The upload route now needs a bearer
    credential the deployment signed (the seam's cheap half) and a multipart body, both judged
    before the slot and before ``receive`` is touched."""

    @pytest.mark.parametrize(
        ("label", "authorization"),
        [
            ("no credential", None),
            ("a credential the check refuses", b"Bearer forged"),
            ("another scheme", b"Basic " + GOOD_TOKEN.encode()),
            ("a bearer with nothing after it", b"Bearer "),
        ],
    )
    def test_an_upload_without_a_signed_credential_is_refused_before_its_slot_and_its_body(
        self, label: str, authorization: bytes | None
    ) -> None:
        async def scenario() -> None:
            inner = HoldingApp()
            app, gate = stack(inner)
            answer = await drive(app, authorization=authorization, chunks=(b"y" * 1000,))
            assert answer.status == 401, (label, answer.status)
            assert answer.envelope["error_code"] == "authentication_required"
            assert answer.receives == 0, f"{label}: the body was touched"
            assert inner.entered == 0 and gate.gate.in_flight == 0

        run(scenario())

    def test_strangers_cannot_hold_the_two_slots(self) -> None:
        async def scenario() -> None:
            inner = HoldingApp()
            app, gate = stack(inner)
            strangers = [await drive(app, authorization=None) for _ in range(4)]
            assert [s.status for s in strangers] == [401] * 4
            held = [asyncio.create_task(drive(app)) for _ in range(2)]
            await until(lambda: inner.entered == 2, "two signed uploads inside the application")
            assert gate.gate.in_flight == 2
            inner.release.set()
            assert [(await h).status for h in held] == [204, 204]

        run(scenario())

    @pytest.mark.parametrize(
        "content_type",
        [
            JSON_TYPE,
            b"application/x-www-form-urlencoded",
            b"text/plain; boundary=x",
            b"text/plain; x=multipart/form-data; boundary=y",
        ],
    )
    def test_a_signed_upload_that_is_not_multipart_is_refused_before_its_body(
        self, content_type: bytes
    ) -> None:
        async def scenario() -> None:
            inner = HoldingApp()
            app, gate = stack(inner)
            answer = await drive(app, content_type=content_type, chunks=(b"y" * 1000,))
            assert answer.status == 422
            assert answer.envelope["details"] == {"field": "Content-Type", "constraint": "media_type"}
            assert answer.receives == 0 and inner.entered == 0 and gate.gate.in_flight == 0

        run(scenario())

    def test_no_check_admits_nobody(self) -> None:
        async def scenario() -> None:
            inner = HoldingApp()
            app, _ = stack(inner, verify_credential=None)
            assert (await drive(app)).status == 401
            assert inner.entered == 0

        run(scenario())

    def test_every_other_route_is_left_to_the_seam(self) -> None:
        async def scenario() -> None:
            app, _ = stack(ConsumingApp())
            for kwargs in ({"path": OTHER_PATH}, {"method": "GET", "content_type": None}):
                answer = await drive(app, authorization=None, **kwargs)
                assert answer.status == 204, kwargs

        run(scenario())

    def test_the_real_check_is_the_seams_signature_and_expiry(self) -> None:
        from auditmanager.api.security import API_TOKEN_VARIABLE, Subject, build_credential_precheck, build_signer

        environ = {API_TOKEN_VARIABLE: "w55b-fix-deployment-secret"}
        check = build_credential_precheck(environ)
        subject = Subject(user_uid="usr_01M2545JSD15ETSNNV904X991S", login="a@b.invalid", token_epoch=1, display_label="A")
        signer = build_signer(environ)
        other = build_signer({API_TOKEN_VARIABLE: "another-deployment"})
        assert signer is not None and other is not None
        assert check(signer.issue(subject, is_default_credential=False).token) is True
        assert check(other.issue(subject, is_default_credential=False).token) is False
        assert check(signer.issue(subject, is_default_credential=False, now=0).token) is False  # expired
        assert check("am2.not.signed") is False
        assert build_credential_precheck({})("anything") is False


class TestTheUploadFormIsParsedUnderSmallBounds:
    """`W55B-FIX` (X-3): Starlette's defaults are a thousand files and a thousand text fields of
    a MiB each. ``uploadDocument``'s route reads two files, four text parts and 16 KiB a text
    part; past them the parser's refusal is ``readable_multipart``."""

    @staticmethod
    def client() -> Any:
        from fastapi import APIRouter, Form

        from auditmanager.api.routers import install_exception_handlers
        from auditmanager.api.routers.correlation import CorrelationMiddleware
        from auditmanager.api.routers.multipart import (
            UPLOAD_FORM_MAX_FIELDS,
            UPLOAD_FORM_MAX_FILES,
            UPLOAD_FORM_MAX_PART_BYTES,
            UploadRoute,
        )

        assert (UPLOAD_FORM_MAX_FILES, UPLOAD_FORM_MAX_FIELDS, UPLOAD_FORM_MAX_PART_BYTES) == (2, 4, 16384)
        app = FastAPI()
        router = APIRouter()

        async def endpoint(
            project_uid: str, file: UploadFile = File(...), title: str = Form(None)
        ) -> dict[str, int]:
            return {"ok": 1}

        router.add_api_route(UPLOAD_PATH.replace("prj_01ARZ3NDEKTSV4RRFFQ69G5FAV", "{project_uid}"),
                             endpoint, methods=["POST"], route_class_override=UploadRoute)
        app.include_router(router)
        install_exception_handlers(app)
        app.add_middleware(CorrelationMiddleware)
        return TestClient(app, raise_server_exceptions=False)

    @pytest.mark.parametrize(
        ("label", "parts", "status"),
        [
            ("a file and a title", ((FILE_PART, PDF), ('form-data; name="title"', b"T")), 200),
            ("two files", ((FILE_PART, PDF), ('form-data; name="other"; filename="b.pdf"', PDF)), 200),
            ("three files", tuple((f'form-data; name="f{i}"; filename="b.pdf"', PDF) for i in range(3)), 422),
            ("four text parts", ((FILE_PART, PDF), *((f'form-data; name="t{i}"', b"x") for i in range(4))), 200),
            ("five text parts", ((FILE_PART, PDF), *((f'form-data; name="t{i}"', b"x") for i in range(5))), 422),
            ("a 16 KiB text part", ((FILE_PART, PDF), ('form-data; name="title"', b"x" * 16384)), 200),
            ("a text part a byte over", ((FILE_PART, PDF), ('form-data; name="title"', b"x" * 16385)), 422),
        ],
    )
    def test_the_bounds_hold_at_their_value_and_refuse_one_more(
        self, label: str, parts: tuple[tuple[str, bytes], ...], status: int
    ) -> None:
        response = self.client().post(UPLOAD_PATH, headers={"Content-Type": CONTENT_TYPE}, content=_body(*parts))
        assert response.status_code == status, (label, response.text)
        if status == 422:
            assert json.loads(response.content)["details"] == {"field": "body", "constraint": "readable_multipart"}
