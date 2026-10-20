"""``uploadDocumentVersion`` over the edge (`W59-VERSION-UPLOAD-01`).

The service's own rules -- next ordinal, nothing inherited, older facts untouched, the row
lock under concurrency -- are proved in ``tests/integration/ingest/test_next_version.py``.
What is asserted here is the operation: the route, its closed multipart body, its key and its
refusals, driven through this suite's seam with the shipped ``DocumentAdapter`` behind it.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from w13_api_driver import Answer, Request, Surface, dispatch

BOUNDARY = "----w59versionupload"


def _body(content: bytes, *, filename: str, extra: tuple[str, str] | None = None) -> bytes:
    parts = [
        (
            f"--{BOUNDARY}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            "Content-Type: application/zip\r\n\r\n"
        ).encode("utf-8"),
        content,
    ]
    if extra is not None:
        name, value = extra
        parts.append(
            (
                f"\r\n--{BOUNDARY}\r\n"
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n{value}'
            ).encode("utf-8")
        )
    parts.append(f"\r\n--{BOUNDARY}--\r\n".encode("utf-8"))
    return b"".join(parts)


def _headers(key: str) -> dict[str, str]:
    return {
        "Idempotency-Key": key,
        "Content-Type": f"multipart/form-data; boundary={BOUNDARY}",
    }


def _ok(response: Answer) -> dict[str, Any]:
    assert response.status < 300, (response.status, response.body)
    return json.loads(response.body)


def _post(router: Surface, path: str, body: bytes, key: str) -> Answer:
    return dispatch(router, Request.build("POST", path, headers=_headers(key), body=body))


def _create_project(router: Surface, name: str, key: str) -> dict[str, Any]:
    return _ok(
        dispatch(
            router,
            Request.build(
                "POST",
                "/projects",
                headers={"Idempotency-Key": key, "Content-Type": "application/json"},
                body=json.dumps({"name": name}).encode("utf-8"),
            ),
        )
    )


@pytest.fixture
def first(router: Surface, corpus_bundle: bytes) -> dict[str, Any]:
    """Version 1 of a fresh document, uploaded with a title through ``uploadDocument``."""
    project = _create_project(router, "Проект АР", "w59vu-project")
    body = _body(corpus_bundle, filename="ar_baseline.zip", extra=("display_title", "Альбом АР"))
    return _ok(_post(router, f"/projects/{project['project_uid']}/documents", body, "w59vu-first"))


def _versions_path(version: dict[str, Any]) -> str:
    return f"/projects/{version['project_uid']}/documents/{version['document_uid']}/versions"


def _revision(bundle_around, corpus_pdf: bytes, label: str) -> bytes:
    return bundle_around(corpus_pdf + f"\n% revision {label}\n".encode(), stem=f"revision_{label}")


def _count_versions(session: Session, document_uid: str) -> int:
    return int(
        session.execute(
            text("SELECT count(*) FROM document_version WHERE document_uid = :d"),
            {"d": document_uid},
        ).scalar_one()
    )


def test_the_next_version_is_published_and_becomes_the_current_one(
    router: Surface, first: dict[str, Any], bundle_around, corpus_pdf: bytes
) -> None:
    body = _body(_revision(bundle_around, corpus_pdf, "2"), filename="revision_2.zip")
    response = _post(router, _versions_path(first), body, "w59vu-second")

    assert response.status == 201, response.body
    second = json.loads(response.body)
    assert second["document_uid"] == first["document_uid"]
    assert second["project_uid"] == first["project_uid"]
    assert second["version_uid"] != first["version_uid"]
    assert second["version_ordinal"] == 2
    # The title is the document's; the new version takes none and inherits no classification.
    assert second["display_title"] == "Альбом АР"
    assert second.get("classification") is None

    listed = _ok(dispatch(router, Request.build("GET", f"/documents/{first['document_uid']}/versions")))
    assert [item["version_uid"] for item in listed["items"]] == [
        second["version_uid"],
        first["version_uid"],
    ]
    documents = _ok(
        dispatch(router, Request.build("GET", f"/projects/{first['project_uid']}/documents"))
    )
    assert [item["version_uid"] for item in documents["items"]] == [second["version_uid"]]
    fetched = _ok(dispatch(router, Request.build("GET", f"/versions/{second['version_uid']}")))
    assert fetched == second, "the read and the write disagree about the same version"


def test_an_exact_repeat_replays_and_another_bundle_under_the_key_is_reuse(
    router: Surface, first: dict[str, Any], bundle_around, corpus_pdf: bytes, session: Session
) -> None:
    body = _body(_revision(bundle_around, corpus_pdf, "2"), filename="revision_2.zip")
    created = _ok(_post(router, _versions_path(first), body, "w59vu-replay"))
    replayed = _post(router, _versions_path(first), body, "w59vu-replay")

    assert replayed.status == 201
    assert json.loads(replayed.body) == created
    assert _count_versions(session, first["document_uid"]) == 2

    other = _body(_revision(bundle_around, corpus_pdf, "3"), filename="revision_3.zip")
    reused = _post(router, _versions_path(first), other, "w59vu-replay")
    assert reused.status == 409
    assert json.loads(reused.body)["error_code"] == "idempotency_key_reuse"
    assert _count_versions(session, first["document_uid"]) == 2


@pytest.mark.parametrize("whose", ["another project", "no document"])
def test_a_document_outside_the_named_project_is_not_found(
    router: Surface,
    first: dict[str, Any],
    bundle_around,
    corpus_pdf: bytes,
    session: Session,
    whose: str,
) -> None:
    if whose == "another project":
        stranger = _create_project(router, "Чужой проект", "w59vu-stranger")
        path = f"/projects/{stranger['project_uid']}/documents/{first['document_uid']}/versions"
    else:
        path = f"/projects/{first['project_uid']}/documents/doc_01M2545JSD15ETSNNV904X991H/versions"
    body = _body(_revision(bundle_around, corpus_pdf, "2"), filename="revision_2.zip")

    response = _post(router, path, body, f"w59vu-404-{whose.replace(' ', '-')}")

    assert response.status == 404, response.body
    envelope = json.loads(response.body)
    assert envelope["error_code"] == "not_found"
    # The aggregate names which rule refused, as the operation's description says.
    assert envelope["details"]["aggregate_type"] == "Document", envelope
    assert _count_versions(session, first["document_uid"]) == 1


@pytest.mark.parametrize(
    ("label", "content", "extra", "constraint"),
    [
        ("a title part", None, ("display_title", "Новое имя"), "additionalProperties"),
        ("a section part", None, ("section", "AR"), "additionalProperties"),
        ("a bare PDF", "pdf", None, "portal_bundle_required"),
    ],
)
def test_what_uploadDocument_refuses_and_what_a_further_version_does_not_take_are_refused(
    router: Surface,
    first: dict[str, Any],
    corpus_bundle: bytes,
    corpus_pdf: bytes,
    session: Session,
    label: str,
    content: str | None,
    extra: tuple[str, str] | None,
    constraint: str,
) -> None:
    payload = corpus_pdf if content == "pdf" else corpus_bundle
    body = _body(payload, filename="upload.zip", extra=extra)

    response = _post(router, _versions_path(first), body, f"w59vu-422-{constraint}-{len(label)}")

    assert response.status == 422, (label, response.body)
    envelope = json.loads(response.body)
    assert envelope["error_code"] == "validation_failed"
    assert envelope["details"]["constraint"] == constraint, (label, envelope)
    assert _count_versions(session, first["document_uid"]) == 1


def test_a_version_upload_without_the_key_is_refused_before_anything_happens(
    router: Surface, first: dict[str, Any], bundle_around, corpus_pdf: bytes, session: Session
) -> None:
    response = dispatch(
        router,
        Request.build(
            "POST",
            _versions_path(first),
            headers={"Content-Type": f"multipart/form-data; boundary={BOUNDARY}"},
            body=_body(_revision(bundle_around, corpus_pdf, "2"), filename="revision_2.zip"),
        ),
    )
    assert response.status == 422
    assert json.loads(response.body)["error_code"] == "validation_failed"
    assert _count_versions(session, first["document_uid"]) == 1
