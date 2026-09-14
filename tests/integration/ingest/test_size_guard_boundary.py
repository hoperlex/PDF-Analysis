"""``ENV-SIZE`` must be reachable through the transport, not only underneath it.

Two guards refuse an oversized upload and they are independently breakable:

* the transport's multipart body limit, ``MAX_BODY`` = 26 MiB
  (``api/routers/multipart.py``), which reads the request and is outermost;
* the envelope's ``ENV-SIZE``, ``MAX_BYTES`` = 25 MiB (``ingest/envelope.py``), which
  judges the document.

Every oversize fixture in the repository is over **both**: the AR corpus's
``oversize.pdf`` is 27 303 204 bytes and PC-02's ``PC02-N03`` is 27 303 351, against a
transport limit of 27 262 976. So the transport always answers first, and no test drives
a request that reaches ``ENV-SIZE`` through HTTP. The existing coverage sits underneath
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
through and the envelope is the guard that speaks.
"""

from __future__ import annotations

import os
import uuid

import pytest

from auditmanager.api.app import create_app
from auditmanager.api.routers import dispatch
from auditmanager.api.routers.http import Request
from auditmanager.api.routers.multipart import MAX_BODY
from auditmanager.ingest import MAX_BYTES

#: Between the two limits, with room for the multipart framing on either side. Asserted
#: below rather than trusted: if either limit moves, the window may close or this value
#: may fall outside it, and a test that quietly stopped exercising the guard it names
#: would be worse than no test.
BODY_TARGET = (MAX_BYTES + MAX_BODY) // 2


def _upload(app, project_uid: str, payload: bytes):
    boundary = "----pc02sizeboundary"
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="between.pdf"\r\n'
        "Content-Type: application/pdf\r\n\r\n"
    ).encode() + payload + (
        f"\r\n--{boundary}--\r\n"
    ).encode()
    assert len(body) <= MAX_BODY, (
        f"the framed body is {len(body)}, over the transport limit {MAX_BODY}; this test "
        "would measure the transport guard instead of ENV-SIZE"
    )
    return dispatch(
        app.router,
        Request(
            method="POST",
            path=f"/projects/{project_uid}/documents",
            headers={
                "Idempotency-Key": f"size-{uuid.uuid4().hex[:12]}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
            query={},
            body=body,
        ),
    )


@pytest.fixture(scope="module")
def app():
    assert os.environ.get("DATABASE_URL"), "this suite needs the lane's .env loaded"
    return create_app()


@pytest.fixture(scope="module")
def project_uid(app) -> str:
    import json

    response = dispatch(
        app.router,
        Request(
            method="POST",
            path="/projects",
            headers={
                "content-type": "application/json",
                "Idempotency-Key": f"proj-{uuid.uuid4().hex[:12]}",
            },
            query={},
            body=json.dumps({"name": "ENV-SIZE boundary"}).encode(),
        ),
    )
    assert response.status in (200, 201), response.body
    return json.loads(response.body)["project_uid"]


def test_the_window_between_the_two_guards_is_open() -> None:
    """The premise of this file, asserted before anything depends on it.

    If the transport limit were ever lowered to the envelope's, there would be no body
    that reaches ENV-SIZE over HTTP and the test below could not mean what it says. That
    would be a real finding about the guards, so it fails here loudly rather than leaving
    a test that passes without exercising anything.
    """
    assert MAX_BYTES < MAX_BODY, (
        f"no body can reach ENV-SIZE through the transport: envelope {MAX_BYTES}, "
        f"transport {MAX_BODY}"
    )
    assert MAX_BYTES < BODY_TARGET < MAX_BODY, (
        f"the chosen body size {BODY_TARGET} is not between {MAX_BYTES} and {MAX_BODY}"
    )


def test_a_body_inside_the_window_is_refused_by_the_envelope(app, project_uid) -> None:
    """The envelope answers, and says which rule it broke.

    Asserted on the constraint the envelope publishes rather than only on the status,
    because both guards refuse with the same family of error - the whole point is *which*
    of them spoke.
    """
    import json

    payload = b"%PDF-1.7\n" + b"x" * (BODY_TARGET - 9)
    assert len(payload) > MAX_BYTES, "the payload does not break ENV-SIZE"

    response = _upload(app, project_uid, payload)
    body = json.loads(response.body) if response.body else {}

    assert response.status >= 400, f"an oversized upload was accepted: {response.status}"
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
