"""Probe 5 -- the upload gate and the per-route body caps, on raw sockets (`W55B-QA-01`).

STREAM's gate admits two uploads per API process and refuses a third with ``503
dependency_unavailable`` (``upload_capacity``) and ``Retry-After`` **before its body is
read**. Here the uploads are real TCP connections to the served process that send their
headers and part of a declared body and then wait, so "in flight" is what a slow client
makes it, and "before its body is read" is shown by sending no body at all.

The last two tests cross STREAM's gate with the seam's authentication (`W34`/`W49`): they
ask whether a caller the deployment does not know can take an upload slot, or have its body
read, before it is refused.
"""

from __future__ import annotations

import json
import socket
import time
import uuid

import pytest

from w55b_qa_support import (
    API_PORT,
    HOST,
    committed,
    create_project,
    new_key,
    scalar,
    upload,
)

MiB = 1024 * 1024
DECLARED = 20 * MiB


class Held:
    """One upload request on its own socket: headers and part of the body sent, then held."""

    def __init__(
        self, path: str, token: str | None, *, declared: int = DECLARED, send: int = MiB, json_body: bool = False
    ) -> None:
        self.boundary = "w55bqagate" + uuid.uuid4().hex
        head = (
            f"--{self.boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"held.zip\"\r\n"
            "Content-Type: application/zip\r\n\r\n"
        ).encode()
        lines = [
            f"POST {path} HTTP/1.1",
            f"Host: {HOST}:{API_PORT}",
            "Content-Type: application/json"
            if json_body
            else f"Content-Type: multipart/form-data; boundary={self.boundary}",
            f"Content-Length: {declared}",
            f"Idempotency-Key: {new_key('gate')}",
        ]
        if token is not None:
            lines.append(f"Authorization: Bearer {token}")
        self.sock = socket.create_connection((HOST, API_PORT), timeout=30)
        self.sock.sendall(("\r\n".join(lines) + "\r\n\r\n").encode())
        if send:
            body = head + b"PK\x03\x04" + b"\0" * (send - len(head) - 4)
            self.sock.sendall(body)

    def response(self, timeout: float) -> tuple[int, dict[str, str], bytes] | None:
        """The status, headers and body the server sent within ``timeout``, or ``None``."""
        self.sock.settimeout(timeout)
        data = b""
        try:
            while b"\r\n\r\n" not in data:
                chunk = self.sock.recv(65536)
                if not chunk:
                    break
                data += chunk
        except (TimeoutError, socket.timeout):
            return None
        if b"\r\n\r\n" not in data:
            return None
        head, _, rest = data.partition(b"\r\n\r\n")
        status_line, *header_lines = head.decode("latin-1").split("\r\n")
        headers = {}
        for line in header_lines:
            name, _, value = line.partition(":")
            headers[name.strip().lower()] = value.strip()
        length = int(headers.get("content-length", "0"))
        try:
            while len(rest) < length:
                chunk = self.sock.recv(65536)
                if not chunk:
                    break
                rest += chunk
        except (TimeoutError, socket.timeout):
            pass
        return int(status_line.split()[1]), headers, rest

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass


@pytest.fixture
def gate(api, expert):
    project = create_project(expert, "QA P5 gate")
    held: list[Held] = []
    yield {"project": project, "path": f"/projects/{project}/documents", "held": held}
    for connection in held:
        connection.close()


def _until_admitted(project: str, token: str, *, seconds: float = 20) -> tuple[int, float]:
    """Retry a small valid upload until it is not refused as busy; (status, seconds waited)."""
    started = time.monotonic()
    while True:
        answer = upload(project, committed("ar_baseline_minimal.zip"), token)
        if answer.status != 503 or time.monotonic() - started > seconds:
            return answer.status, time.monotonic() - started
        time.sleep(0.25)


def test_a_third_upload_is_refused_before_its_body_is_read_and_a_disconnect_frees_a_slot(gate, engine, expert) -> None:
    """Expected: with two authenticated uploads holding the gate (headers and 1 MiB of a
    declared 20 MiB sent), a third that sends its headers and **no body** is answered within
    seconds with ``503 dependency_unavailable``, ``details.dependency: upload_capacity`` and a
    ``Retry-After`` header, and nothing is created. When one holder disconnects mid-body, a
    slot is released: a new upload is admitted (``201``) within a few seconds while the other
    holder still waits; when it disconnects too, uploads are admitted again."""
    held = gate["held"]
    held.extend(Held(gate["path"], expert) for _ in range(2))
    time.sleep(1.0)
    versions = scalar(engine, "SELECT count(*) FROM document_version")

    third = Held(gate["path"], expert, send=0)
    held.append(third)
    answered = third.response(timeout=10)
    assert answered is not None, "the third upload was not answered without its body"
    status, headers, body = answered
    assert status == 503, (status, body[:300])
    envelope = json.loads(body)
    assert envelope["error_code"] == "dependency_unavailable"
    assert envelope["details"] == {"dependency": "upload_capacity"}
    assert headers.get("retry-after", "").isdigit(), headers
    assert scalar(engine, "SELECT count(*) FROM document_version") == versions

    held[0].close()
    status, waited = _until_admitted(gate["project"], expert)
    assert status == 201, (status, waited)
    held[1].close()
    status, waited = _until_admitted(gate["project"], expert)
    assert status == 201, (status, waited)


def test_every_other_route_keeps_its_cap_and_the_upload_route_its_own(api, expert) -> None:
    """Expected: a JSON route declaring a 27 MiB JSON body (over the 26 MiB general cap) is refused
    ``validation_failed`` / ``max_bytes`` on ``field: body`` before its body is sent; the upload
    route declaring 252 MiB (over its 251 MiB cap) is refused the same way on ``field: file``."""
    cases = (
        ("/projects", 27 * MiB, "body", True),
        ("/projects/prj_01M2545JSD15ETSNNV904X991F/documents", 252 * MiB, "file", False),
    )
    for path, declared, field, json_body in cases:
        connection = Held(path, expert, declared=declared, send=0, json_body=json_body)
        try:
            answered = connection.response(timeout=10)
        finally:
            connection.close()
        assert answered is not None, (path, "not answered without its body")
        status, _headers, body = answered
        envelope = json.loads(body)
        assert envelope["error_code"] == "validation_failed", (path, status, envelope)
        assert envelope["details"] == {"field": field, "constraint": "max_bytes"}, (path, envelope)


def test_an_unauthenticated_upload_is_refused_before_its_body_is_read(gate) -> None:
    """Expected (the seam is fail-closed and the gate exists so a body is not read to be
    refused): an upload with **no credential** that sends its headers and no body is answered
    ``401 authentication_required`` within seconds -- the server does not wait for, read or
    spool a body it will refuse."""
    anonymous = Held(gate["path"], None, send=0)
    gate["held"].append(anonymous)
    answered = anonymous.response(timeout=5)
    assert answered is not None, (
        "no answer within 5 s: the server waits for the body of an unauthenticated upload "
        "before refusing it"
    )
    assert answered[0] == 401, answered[:2]


def _forged() -> str:
    """A well-formed credential signed with a key this deployment does not hold."""
    from auditmanager.api.security import Subject, build_signer

    signer = build_signer({"AUDITMANAGER_API_TOKEN": "w55b-qa-another-deployment"})
    assert signer is not None
    return signer.issue(
        Subject(user_uid="usr_01M2545JSD15ETSNNV904X991S", login="x@suite.invalid", token_epoch=1, display_label="X"),
        is_default_credential=False,
    ).token


@pytest.mark.parametrize("caller", ["no_credential", "forged_credential"])
def test_unauthenticated_callers_cannot_hold_the_upload_slots(gate, expert, caller) -> None:
    """Expected: two uploads with **no credential** (or a credential this deployment did not
    sign), each holding its connection mid-body, do not take the deployment's two upload
    slots: an authenticated upload sent meanwhile is admitted (``201``), not refused ``503
    upload_capacity``."""
    token = None if caller == "no_credential" else _forged()
    gate["held"].extend(Held(gate["path"], token) for _ in range(2))
    time.sleep(1.0)
    answer = upload(gate["project"], committed("ar_baseline_minimal.zip"), expert)
    assert answer.status == 201, answer
