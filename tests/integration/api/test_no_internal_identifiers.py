"""No bucket, object key, filename or filesystem path crosses the boundary.

Proved by **walking real response bodies**, not by reading the routers. A source read
shows what the code appears to emit; a walk shows what it actually emitted, including
whatever a domain record carried along that nobody thought about. The bodies here come
from the whole surface driven against real PostgreSQL and a real private bucket, so the
values under inspection are the real bucket name, the real object key layout and the
real uploaded filename -- taken from the environment and from the fixtures rather than
guessed at.

``P02_SEAMS.md`` section 2.2 gives the list this module enforces: filesystem path,
directory name, uploaded file name, S3 object key, bucket name, URL or presigned link,
display ordinal as an identity, provider request id, model name, prompt text,
idempotency key, payload fingerprint, execution token, content checksum as an identity.

The one thing that *is* allowed to be blob-facing is ``blob_id``, and it is opaque:
``auditmanager.storage`` derives it from ``(sha256, size)``, so it addresses content
rather than a location and there is no accessor that turns one back into a key.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Iterator

import pytest
from sqlalchemy.orm import Session

from auditmanager.documents import MANIFEST_ROLE_SOURCE_DOCUMENT
from w13_api_driver import Answer, Request, Surface, dispatch
from auditmanager.storage import S3StorageSettings

from .conftest import PublishedRun

#: The uploaded file name the suite really uploads under.
SOURCE_FILENAME = "ar_baseline.pdf"


def walk(value: Any, path: str = "$") -> Iterator[tuple[str, Any]]:
    """Every scalar in a decoded body, with the path that reached it.

    Recursive on purpose: a leaked key three levels down inside a manifest entry is
    exactly the kind a top-level field check misses.
    """
    if isinstance(value, dict):
        for key, item in value.items():
            yield f"{path}.{key}", key
            yield from walk(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from walk(item, f"{path}[{index}]")
    else:
        yield path, value


@pytest.fixture(scope="session")
def forbidden_values() -> tuple[str, ...]:
    """The real values that must not appear, read from the environment and fixtures."""
    settings = S3StorageSettings.from_env()
    values = [
        settings.bucket,
        settings.endpoint_url,
        SOURCE_FILENAME,
        "ar_baseline",
    ]
    return tuple(value for value in values if value)


#: Shapes that are forbidden whatever their value: a path, a URL, an S3 URI.
_FORBIDDEN_SHAPES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("an absolute filesystem path", re.compile(r"(^|[\s\"'])/(?:[\w.-]+/)+[\w.-]+")),
    ("a Windows path", re.compile(r"\b[A-Za-z]:\\")),
    ("a URL", re.compile(r"\b[a-z][a-z0-9+.-]*://", re.I)),
    ("an s3 URI", re.compile(r"\bs3://", re.I)),
    ("a PDF filename", re.compile(r"\b[\w.-]+\.pdf\b", re.I)),
)

#: Property names no response may carry. `blob_id` is deliberately absent from the
#: forbidden list and deliberately absent from every frozen response schema too: the
#: manifest carries a checksum and a role, and the identity stays server-side.
_FORBIDDEN_KEYS = frozenset(
    {
        "bucket",
        "bucket_name",
        "object_key",
        "key",
        "s3_key",
        "path",
        "file_path",
        "filename",
        "file_name",
        "source_filename",
        "url",
        "href",
        "download_url",
        "presigned_url",
        "location",
        "prompt",
        "prompt_text",
        "idempotency_key",
        "payload_fingerprint",
        "execution_token",
        "sequence_no",
    }
)


#: Fields whose value the *caller* supplied, so their content cannot be a leak of internal
#: state: the client already knows it, having sent it. The shape scan skips these and the
#: forbidden-value and forbidden-key scans still apply to them, because a caller-supplied
#: label must still never be a bucket or an object key.
#:
#: This exists because the guard fired on `Project.name`. The frozen contract calls it a
#: "Display label. Not unique and not an identity", a journey fixture named a project
#: "B-III negative encrypted.pdf", and the PDF-filename shape matched - reporting a leak
#: where the only thing that had crossed the boundary was the client's own text coming
#: back. A user may legitimately name a project after a document.
_CALLER_SUPPLIED_FIELDS = frozenset({"name", "comment", "display_title"})


def assert_clean(body: Any, forbidden_values: tuple[str, ...], where: str) -> None:
    for path, value in walk(body):
        if isinstance(value, str):
            for forbidden in forbidden_values:
                assert forbidden not in value, (
                    f"{where}: {path} carries {forbidden!r}, which is an internal address"
                )
            if path.rsplit(".", 1)[-1] in _CALLER_SUPPLIED_FIELDS:
                continue
            for what, pattern in _FORBIDDEN_SHAPES:
                assert not pattern.search(value), (
                    f"{where}: {path} carries {what}: {value!r}"
                )
    for path, value in walk(body):
        if path.endswith(tuple(f".{name}" for name in _FORBIDDEN_KEYS)):
            raise AssertionError(
                f"{where}: {path} is a property no response may carry"
            )


def _headers_and_body(response: Answer) -> tuple[dict[str, str], Any]:
    headers = {name: value for name, value in response.headers}
    content_type = headers.get("Content-Type", "")
    if "json" in content_type:
        return headers, json.loads(response.body)
    return headers, None


# ---------------------------------------------------------------------------


def test_the_whole_surface_leaks_nothing(
    router: Surface,
    corpus_pdf: bytes,
    published_run: PublishedRun,
    forbidden_values: tuple[str, ...],
) -> None:
    """Drive every reachable operation and walk each response body and header set."""
    assert forbidden_values, "nothing to check against; the fixture found no real values"

    project = json.loads(
        dispatch(
            router,
            Request.build(
                "POST",
                "/projects",
                headers={"Idempotency-Key": "k-1", "Content-Type": "application/json"},
                body=json.dumps({"name": "Проект"}).encode("utf-8"),
            ),
        ).body
    )

    boundary = "----b6"
    upload_body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{SOURCE_FILENAME}"\r\n'
        "Content-Type: application/pdf\r\n\r\n"
    ).encode("utf-8") + corpus_pdf + (
        f"\r\n--{boundary}--\r\n"
    ).encode("utf-8")

    requests = {
        "createProject": Request.build(
            "POST",
            "/projects",
            headers={"Idempotency-Key": "k-2", "Content-Type": "application/json"},
            body=json.dumps({"name": "Второй"}).encode("utf-8"),
        ),
        "listProjects": Request.build("GET", "/projects"),
        "uploadDocument": Request.build(
            "POST",
            f"/projects/{project['project_uid']}/documents",
            headers={
                "Idempotency-Key": "k-3",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
            body=upload_body,
        ),
        "getRunStatus": Request.build("GET", f"/runs/{published_run.run_id}"),
        "listRunFindings": Request.build(
            "GET", f"/runs/{published_run.run_id}/findings"
        ),
        "getFinding": Request.build("GET", f"/findings/{published_run.finding_uid}"),
        "appendDecision": Request.build(
            "POST",
            f"/findings/{published_run.finding_uid}/decisions",
            headers={"Idempotency-Key": "k-4", "Content-Type": "application/json"},
            body=json.dumps(
                {
                    "event_type": "comment",
                    "finding_observation_id": published_run.finding_observation_id,
                    "comment": "Проверено.",
                }
            ).encode("utf-8"),
        ),
        "listDecisionHistory": Request.build(
            "GET", f"/findings/{published_run.finding_uid}/decisions"
        ),
    }

    uploaded: dict[str, Any] | None = None
    for operation, request in requests.items():
        response = dispatch(router, request)
        assert response.status < 400, (operation, response.status, response.body)
        headers, body = _headers_and_body(response)
        if body is not None:
            assert_clean(body, forbidden_values, operation)
        assert_clean(headers, forbidden_values, f"{operation} headers")
        if operation == "uploadDocument":
            uploaded = body

    assert uploaded is not None

    # The two operations that need the uploaded version.
    for operation, request in {
        "getDocumentVersion": Request.build(
            "GET", f"/versions/{uploaded['version_uid']}"
        ),
    }.items():
        response = dispatch(router, request)
        assert response.status == 200, (operation, response.body)
        headers, body = _headers_and_body(response)
        assert_clean(body, forbidden_values, operation)
        assert_clean(headers, forbidden_values, f"{operation} headers")


def test_the_uploaded_filename_never_comes_back(
    router: Surface, corpus_pdf: bytes, forbidden_values: tuple[str, ...]
) -> None:
    """The name really was supplied, and really is absent from the response.

    Without the first half this asserts nothing: a filename that was never sent cannot
    leak. The upload below carries a distinctive name, and the whole response body is
    then searched for it.
    """
    project = json.loads(
        dispatch(
            router,
            Request.build(
                "POST",
                "/projects",
                headers={"Idempotency-Key": "f-1", "Content-Type": "application/json"},
                body=json.dumps({"name": "Проект"}).encode("utf-8"),
            ),
        ).body
    )
    distinctive = "very-distinctive-source-name.pdf"
    boundary = "----b6"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{distinctive}"\r\n'
        "Content-Type: application/pdf\r\n\r\n"
    ).encode("utf-8") + corpus_pdf + (f"\r\n--{boundary}--\r\n").encode("utf-8")

    response = dispatch(
        router,
        Request.build(
            "POST",
            f"/projects/{project['project_uid']}/documents",
            headers={
                "Idempotency-Key": "f-2",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
            body=body,
        ),
    )
    assert response.status == 201, response.body
    raw = response.body.decode("utf-8")
    assert distinctive not in raw, "the uploaded file name came back in the response"
    assert "very-distinctive-source-name" not in raw

    version = json.loads(raw)
    fetched = dispatch(router, Request.build("GET", f"/versions/{version['version_uid']}"))
    assert distinctive not in fetched.body.decode("utf-8")


def test_the_streamed_content_response_carries_no_address(
    router: Surface, corpus_pdf: bytes, forbidden_values: tuple[str, ...]
) -> None:
    """The viewer receives bytes, and its headers name no location.

    Specifically: no ``Location`` header, no redirect status, and no presigned URL
    anywhere in the header set. The bytes themselves are the fixture's, so their
    content is not searched -- a PDF legitimately contains its own internal names.
    """
    project = json.loads(
        dispatch(
            router,
            Request.build(
                "POST",
                "/projects",
                headers={"Idempotency-Key": "s-1", "Content-Type": "application/json"},
                body=json.dumps({"name": "Проект"}).encode("utf-8"),
            ),
        ).body
    )
    boundary = "----b6"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{SOURCE_FILENAME}"\r\n'
        "Content-Type: application/pdf\r\n\r\n"
    ).encode("utf-8") + corpus_pdf + (f"\r\n--{boundary}--\r\n").encode("utf-8")
    version = json.loads(
        dispatch(
            router,
            Request.build(
                "POST",
                f"/projects/{project['project_uid']}/documents",
                headers={
                    "Idempotency-Key": "s-2",
                    "Content-Type": f"multipart/form-data; boundary={boundary}",
                },
                body=body,
            ),
        ).body
    )

    response = dispatch(
        router, Request.build("GET", f"/versions/{version['version_uid']}/content")
    )
    assert response.status == 200, response.body
    assert response.body == corpus_pdf, "the server did not stream the real bytes"

    headers = {name: value for name, value in response.headers}
    assert "Location" not in headers, "a redirect is not how this content is served"
    assert response.status not in (301, 302, 303, 307, 308)
    assert_clean(headers, forbidden_values, "streamDocumentVersionContent headers")


def test_an_export_disposition_names_only_the_opaque_run_identity(
    router: Surface, session: Session, forbidden_values: tuple[str, ...]
) -> None:
    """The one filename the document allows is built from an opaque identity.

    The frozen ``exportRunCsv`` 200 declares a ``Content-Disposition`` whose file name
    is "presentation only and never an identity". This checks it is the run identity and
    a suffix, and nothing else -- no project label, no source name, no path.
    """
    run = PublishedRun(session, state="published")
    response = dispatch(router, Request.build("GET", f"/runs/{run.run_id}/export.csv"))
    assert response.status == 200, response.body

    headers = {name: value for name, value in response.headers}
    disposition = headers["Content-Disposition"]
    assert disposition == f'attachment; filename="{run.run_id}.csv"'
    for forbidden in forbidden_values:
        assert forbidden not in disposition


def test_an_error_envelope_leaks_nothing_either(
    router: Surface, published_run: PublishedRun, forbidden_values: tuple[str, ...]
) -> None:
    """Failures are walked too. A leak is at least as likely on a failure path."""
    cases = (
        Request.build("GET", "/versions/ver_01M2545JSD15ETSNNV904X991J"),
        Request.build("GET", "/findings/not-an-identity"),
        Request.build("GET", "/projects?cursor=%20%2Fetc%2Fpasswd"),
        Request.build(
            "POST",
            "/projects",
            headers={"Idempotency-Key": "/etc/passwd", "Content-Type": "application/json"},
            body=b'{"name": "x"}',
        ),
        Request.build(
            "POST",
            "/projects",
            headers={"Idempotency-Key": "e-1", "Content-Type": "application/json"},
            body=json.dumps({"name": "x", "/etc/passwd": 1}).encode("utf-8"),
        ),
    )
    for index, request in enumerate(cases):
        response = dispatch(router, request)
        assert response.status >= 400, (index, response.status)
        assert_clean(json.loads(response.body), forbidden_values, f"error[{index}]")


def test_the_walk_can_fail(forbidden_values: tuple[str, ...]) -> None:
    """The detector detects.

    Every assertion above is only worth its runtime if ``assert_clean`` rejects a body
    that really does carry an address. Five shapes, each of which a real leak would
    take.
    """
    leaks = (
        {"download_url": "https://minio.internal/audit-b6/objects/ab/cd.pdf"},
        {"nested": [{"deep": {"path": "/var/lib/audit/objects/ab/cd.pdf"}}]},
        {"source_filename": SOURCE_FILENAME},
        {"note": f"stored in bucket {forbidden_values[0]}"},
        {"items": [{"object_key": "sources/ab/cd"}]},
    )
    for index, body in enumerate(leaks):
        with pytest.raises(AssertionError):
            assert_clean(body, forbidden_values, f"leak[{index}]")

    # And it passes what it should pass, so it is not simply rejecting everything.
    assert_clean(
        {
            "version_uid": "ver_01M2545JSD15ETSNNV904X991J",
            "input_manifest": [
                {"role": MANIFEST_ROLE_SOURCE_DOCUMENT, "sha256": "a" * 64, "size_bytes": 1},
            ],
        },
        forbidden_values,
        "clean",
    )


def test_the_caller_supplied_exemption_is_narrow() -> None:
    """Exempting a display label from the *shape* scan must not exempt it from the rest.

    The exemption exists because a user may legitimately name a project after a document,
    and the client already knows the text it sent. It would be worthless if it also let an
    object key ride back inside that field, so the forbidden-value and forbidden-key scans
    still apply there. Three cases, because an exemption nobody has probed is indistinguishable
    from a hole.
    """
    # 1. A filename in a caller-supplied label is allowed: the client sent it.
    assert_clean(
        {"items": [{"name": "Отчёт encrypted.pdf"}]},
        ("audit-b6",),
        "caller label",
    )

    # 2. The same text in a field the server generates is still a leak.
    with pytest.raises(AssertionError, match="a PDF filename"):
        assert_clean({"items": [{"source_label": "encrypted.pdf"}]}, (), "server field")

    # 3. An internal address inside the exempt field is still refused, by value...
    with pytest.raises(AssertionError, match="internal address"):
        assert_clean({"items": [{"name": "audit-b6/objects/ab/cd"}]}, ("audit-b6",), "label")

    # ...and a forbidden property name is still refused whatever the exemption.
    with pytest.raises(AssertionError, match="no response may carry"):
        assert_clean({"items": [{"object_key": "anything"}]}, (), "label")
