"""``ENV-SIZE`` must be reachable through the transport, not only underneath it.

Two guards refuse an oversized upload and they are independently breakable:

* the transport's multipart body limit for the upload route, ``UPLOAD_MAX_BODY`` = 251 MiB
  (``api/routers/multipart.py``; it was ``MAX_BODY`` = 26 MiB, which is still every other
  route's limit), which reads the request and is outermost;
* the envelope's ``ENV-SIZE``, ``MAX_BYTES`` = 250 MiB (``ingest/envelope.py``; it was
  25 MiB until `W55B-INGEST-01`), which judges the document.

Every oversize fixture in the repository used to be over **both**: the AR corpus's
``oversize.pdf`` is 27 303 204 bytes and PC-02's ``PC02-N03`` is 27 303 351, against a
transport limit of 27 262 976. So the transport always answered first, and no test drove
a request that reached ``ENV-SIZE`` through HTTP. The existing coverage sits underneath
the transport - ``test_negative_envelope.py`` imports ``auditmanager.ingest`` directly,
and ``fixtures_ar/test_negative_fixtures.py`` calls ``envelope.check`` on a byte string -
so ``ENV-SIZE`` could stop being applied on the HTTP path with every suite still green.

P4-RUN-01 found this from the other end: it reported that ``PC02-N03`` is refused with
``constraint: max_bytes`` rather than ``byte_size <= 26214400``, and read it as a gap in
the PC-02 corpus. It is not a corpus gap. The corpus builder fixes 2-4 negative documents
and already has 4, so a fifth cannot be added, and the same hole exists in the AR corpus.
It is a missing test, and a test can make its own body without touching either frozen
corpus - which is the right tool, because changing corpus bytes would invalidate a
measurement that has already been taken.

The body here is sized into the window between the two limits, so the transport passes it
through and the envelope is the guard that speaks. **`W55B-STREAM-01`** moved the upper end
of that window from 26 MiB to the upload route's 251 MiB, and **`W55B-INGEST-01`** moved its
lower end from 25 MiB to 250 MiB (the plan's "precheck 250 MiB < API cap < nginx 260m"): the
window is one mebibyte wide now, less the multipart framing, and the body sits 256 KiB into
it. It is *streamed* -- a header, a hole of zeros in 1 MiB pieces and the closing framing --
so the test process never holds 250 MiB, and the server spools it to a temporary file as it
does for a browser.
"""

from __future__ import annotations

import os
import uuid

import pytest

from starlette.testclient import TestClient

from auditmanager.api.app import create_app, create_asgi_app
from auditmanager.api.routers.multipart import MAX_BODY, UPLOAD_MAX_BODY
from auditmanager.api.security import API_TOKEN_VARIABLE
from auditmanager.ingest import MAX_BYTES

#: `T-6`. The deployment secret this suite configures, as a literal; the credential it
#: presents is minted from it below.
DEPLOYMENT_SECRET = "size-guard-static-token"

_STATIC_TOKEN_CACHE: str | None = None


def static_token() -> str:
    """A credential this lane's API accepts, for an account this lane really has.

    **Lazy and memoised on purpose.** It opens a database connection, and doing that at
    import time would turn a lane whose services are not up into a *collection* error --
    which reads as a broken suite rather than as an absent lane.

    `W39-REVOKE`: a credential is refused unless the account it names exists and still
    accepts that credential's generation, so this suite's old habit of minting for an
    identity it invented is now presenting something the seam is correct to reject. The row
    is written, the epoch is read back out of it, and the credential is minted from what the
    database says. See ``tests/support/accounts.py``.
    """
    global _STATIC_TOKEN_CACHE
    if _STATIC_TOKEN_CACHE is None:
        from am_test_accounts import provisioned_credential

        _STATIC_TOKEN_CACHE = provisioned_credential(DEPLOYMENT_SECRET, "size-guard-suite")
    return _STATIC_TOKEN_CACHE


#: Between the two limits, with room for the multipart framing on either side. Asserted
#: below rather than trusted: if either limit moves, the window may close or this value
#: may fall outside it, and a test that quietly stopped exercising the guard it names
#: would be worse than no test. 256 KiB past the envelope's bound, a mebibyte under the
#: transport's.
BODY_TARGET = MAX_BYTES + 256 * 1024

_PIECE = b"\0" * (1024 * 1024)


def _framed(payload_size: int, head: bytes, filename: str) -> tuple[dict[str, str], int, object]:
    """(headers, framed length, a chunk iterator) for a part of ``payload_size`` bytes that
    begins with ``head`` and is zeros after it. Nothing larger than 1 MiB is ever held."""
    boundary = "----pc02sizeboundary"
    opening = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        "Content-Type: application/pdf\r\n\r\n"
    ).encode() + head
    closing = f"\r\n--{boundary}--\r\n".encode()

    def chunks():
        yield opening
        remaining = payload_size - len(head)
        while remaining > 0:
            piece = _PIECE if remaining >= len(_PIECE) else _PIECE[:remaining]
            yield piece
            remaining -= len(piece)
        yield closing

    headers = {
        "Authorization": f"Bearer {static_token()}",
        "Idempotency-Key": f"size-{uuid.uuid4().hex[:12]}",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    }
    return headers, len(opening) + (payload_size - len(head)) + len(closing), chunks()


def _upload(app, project_uid: str, payload_size: int, head: bytes = b"%PDF-1.7\n"):
    headers, framed, chunks = _framed(payload_size, head, "between.pdf")
    assert framed <= UPLOAD_MAX_BODY, (
        f"the framed body is {framed}, over the transport limit {UPLOAD_MAX_BODY}; this "
        "test would measure the transport guard instead of ENV-SIZE"
    )
    return app.client.post(
        f"/projects/{project_uid}/documents", headers=headers, content=chunks
    )


class _Composed:
    """The built application and an ASGI client over what serves it.

    Re-pointed by `W13-API`: the two guards are unchanged and still independently
    breakable, but the outer one is now ``BodyCapMiddleware`` in front of the routing
    rather than a call inside a hand-written reader, so the only way to ask which of them
    answered is to drive the transport.
    """

    __slots__ = ("application", "client")

    def __init__(self, application, client) -> None:
        self.application = application
        self.client = client


@pytest.fixture(scope="module")
def app():
    assert os.environ.get("DATABASE_URL"), "this suite needs the lane's .env loaded"
    environ = dict(os.environ) | {API_TOKEN_VARIABLE: DEPLOYMENT_SECRET}
    application = create_app(environ=environ)
    asgi = create_asgi_app(environ=environ, application=application)
    return _Composed(application, TestClient(asgi, raise_server_exceptions=False))


@pytest.fixture(scope="module")
def project_uid(app) -> str:
    import json

    response = app.client.post(
        "/projects",
        headers={
            "Authorization": f"Bearer {static_token()}",
            "content-type": "application/json",
            "Idempotency-Key": f"proj-{uuid.uuid4().hex[:12]}",
        },
        content=json.dumps({"name": "ENV-SIZE boundary"}).encode(),
    )
    assert response.status_code in (200, 201), response.content
    return json.loads(response.content)["project_uid"]


def test_the_window_between_the_two_guards_is_open() -> None:
    """The premise of this file, asserted before anything depends on it.

    If the transport limit were ever lowered to the envelope's, there would be no body
    that reaches ENV-SIZE over HTTP and the test below could not mean what it says. That
    would be a real finding about the guards, so it fails here loudly rather than leaving
    a test that passes without exercising anything.
    """
    assert MAX_BYTES < UPLOAD_MAX_BODY, (
        f"no body can reach ENV-SIZE through the transport: envelope {MAX_BYTES}, "
        f"transport {UPLOAD_MAX_BODY}"
    )
    assert MAX_BYTES < BODY_TARGET < UPLOAD_MAX_BODY, (
        f"the chosen body size {BODY_TARGET} is not between {MAX_BYTES} and "
        f"{UPLOAD_MAX_BODY}"
    )
    # The target also stays under the limit every *other* route keeps, so the body here is
    # the same one that was inside the window before the upload route's cap moved.
    # The ordinary routes' cap is far below the envelope's now, so a body this size could
    # never have reached the envelope on any other route -- which is the reason the upload
    # route has a cap of its own.
    assert MAX_BODY < MAX_BYTES, (
        f"an ordinary route's cap {MAX_BODY} is not below the envelope's {MAX_BYTES}"
    )


def test_a_body_inside_the_window_is_refused_by_the_envelope(app, project_uid) -> None:
    """The envelope answers, and says which rule it broke.

    Asserted on the constraint the envelope publishes rather than only on the status,
    because both guards refuse with the same family of error - the whole point is *which*
    of them spoke.
    """
    import json

    assert BODY_TARGET > MAX_BYTES, "the payload does not break ENV-SIZE"

    response = _upload(app, project_uid, BODY_TARGET)
    body = json.loads(response.content) if response.content else {}

    assert response.status_code >= 400, (
        f"an oversized upload was accepted: {response.status_code}"
    )
    # The constraint lives under `details`, where the error envelope puts the machine
    # -readable part; the top level carries the human message. Reading the top level
    # returned "" and made the failure look like the transport had answered, which is the
    # opposite of what happened.
    constraint = str((body.get("details") or {}).get("constraint", ""))
    assert constraint == f"byte_size <= {MAX_BYTES}", (
        "the refusal did not come from ENV-SIZE. Got "
        f"details.constraint={constraint!r}, body={body!r}. `max_bytes` means the "
        "transport guard answered first, which is the condition this test exists to "
        "detect."
    )


def test_a_body_past_the_limit_every_other_route_keeps_still_reaches_the_envelope(
    app, project_uid
) -> None:
    """`W55B-STREAM-01`: the upload route's cap moved, and this is the body that shows it.

    ``MAX_BODY`` (26 MiB) is still the cap of every route that is not an upload; for
    ``uploadDocument`` it was the transport's limit until that lane, and a body one byte
    over it was refused as ``max_bytes`` (``records/22``). It now passes the transport. Since
    `W55B-INGEST-01` the envelope's bound is 250 MiB, so this body is no longer *too big*:
    it is a PDF header and zeros, and the envelope judges what it holds -- a document it
    cannot parse -- which is the proof that it was the envelope, and not the transport, that
    answered.
    """
    import json

    size = MAX_BODY                      # the framed body is then past the ordinary cap
    headers, framed, chunks = _framed(size, b"%PDF-1.7\n", "past.pdf")
    assert MAX_BODY < framed <= UPLOAD_MAX_BODY
    response = app.client.post(
        f"/projects/{project_uid}/documents", headers=headers, content=chunks
    )
    body = json.loads(response.content)

    assert response.status_code == 422, response.content[:300]
    assert (body.get("details") or {}).get("constraint") == "parseable_pdf", body
