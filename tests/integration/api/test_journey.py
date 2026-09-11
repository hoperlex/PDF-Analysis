"""The PC-01 journey through the routers, against real PostgreSQL and real MinIO.

One project, one AR PDF, one run's findings, one decision, one CSV -- which is what the
frozen document's own summary says the surface is for. Everything here goes through
``dispatch``, so the error middleware, the correlation header and the idempotency
contract are all in the path rather than bypassed.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.documents import MANIFEST_ROLE_SOURCE_DOCUMENT
from auditmanager.api.routers import Router, dispatch
from auditmanager.api.routers.http import Request, Response

from .conftest import PublishedRun

BOUNDARY = "----b6journey"


def upload_body(content: bytes, *, filename: str, title: str | None = None) -> bytes:
    parts = [
        (
            f"--{BOUNDARY}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            "Content-Type: application/pdf\r\n\r\n"
        ).encode("utf-8"),
        content,
    ]
    if title is not None:
        parts.append(
            (
                f"\r\n--{BOUNDARY}\r\n"
                'Content-Disposition: form-data; name="display_title"\r\n\r\n'
                f"{title}"
            ).encode("utf-8")
        )
    parts.append(f"\r\n--{BOUNDARY}--\r\n".encode("utf-8"))
    return b"".join(parts)


def multipart_headers(key: str) -> dict[str, str]:
    return {
        "Idempotency-Key": key,
        "Content-Type": f"multipart/form-data; boundary={BOUNDARY}",
    }


def json_headers(key: str) -> dict[str, str]:
    return {"Idempotency-Key": key, "Content-Type": "application/json"}


def ok(response: Response) -> dict[str, Any]:
    assert response.status < 300, (response.status, response.body)
    return json.loads(response.body)


@pytest.fixture
def project(router: Router) -> dict[str, Any]:
    return ok(
        dispatch(
            router,
            Request.build(
                "POST",
                "/projects",
                headers=json_headers("journey-project"),
                body=json.dumps({"name": "Проект АР"}).encode("utf-8"),
            ),
        )
    )


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------


def test_the_ingest_path_publishes_an_immutable_version(
    router: Router, project: dict[str, Any], corpus_pdf: bytes
) -> None:
    response = dispatch(
        router,
        Request.build(
            "POST",
            f"/projects/{project['project_uid']}/documents",
            headers=multipart_headers("journey-upload"),
            body=upload_body(corpus_pdf, filename="ar_baseline.pdf", title="Годовой"),
        ),
    )
    assert response.status == 201
    version = json.loads(response.body)

    assert version["project_uid"] == project["project_uid"]
    assert version["media_type"] == "application/pdf"
    assert version["page_count"] >= 1
    assert version["version_ordinal"] == 1
    assert version["byte_size"] == len(corpus_pdf)
    assert version["input_manifest"], "a published version carries its input manifest"
    assert {entry["role"] for entry in version["input_manifest"]} == {
        MANIFEST_ROLE_SOURCE_DOCUMENT
    }

    fetched = ok(dispatch(router, Request.build("GET", f"/versions/{version['version_uid']}")))
    assert fetched == version, "the read and the write disagree about the same version"


def test_the_same_key_and_payload_replays_and_creates_nothing(
    router: Router, project: dict[str, Any], corpus_pdf: bytes, session: Session
) -> None:
    """A replay returns the original resource. It does not publish a second version."""
    body = upload_body(corpus_pdf, filename="ar_baseline.pdf")
    first = ok(
        dispatch(
            router,
            Request.build(
                "POST",
                f"/projects/{project['project_uid']}/documents",
                headers=multipart_headers("journey-replay"),
                body=body,
            ),
        )
    )
    second = ok(
        dispatch(
            router,
            Request.build(
                "POST",
                f"/projects/{project['project_uid']}/documents",
                headers=multipart_headers("journey-replay"),
                body=body,
            ),
        )
    )
    assert first == second

    count = session.execute(
        text("SELECT count(*) FROM document_version WHERE document_uid = :d"),
        {"d": first["document_uid"]},
    ).scalar_one()
    assert count == 1, "the replay published a second version"


def test_the_same_key_with_a_different_payload_is_refused(
    router: Router, project: dict[str, Any], corpus_pdf: bytes
) -> None:
    """``idempotency_key_reuse``, and nothing is created."""
    dispatch(
        router,
        Request.build(
            "POST",
            f"/projects/{project['project_uid']}/documents",
            headers=multipart_headers("journey-reuse"),
            body=upload_body(corpus_pdf, filename="first.pdf"),
        ),
    )
    conflicting = dispatch(
        router,
        Request.build(
            "POST",
            f"/projects/{project['project_uid']}/documents",
            headers=multipart_headers("journey-reuse"),
            body=upload_body(corpus_pdf, filename="second.pdf"),
        ),
    )
    assert conflicting.status == 409
    body = json.loads(conflicting.body)
    assert body["error_code"] == "idempotency_key_reuse"
    assert body["retryable"] is False


def test_a_write_without_the_header_is_refused_before_anything_happens(
    router: Router, project: dict[str, Any], corpus_pdf: bytes, session: Session
) -> None:
    before = session.execute(text("SELECT count(*) FROM document_version")).scalar_one()
    response = dispatch(
        router,
        Request.build(
            "POST",
            f"/projects/{project['project_uid']}/documents",
            headers={"Content-Type": f"multipart/form-data; boundary={BOUNDARY}"},
            body=upload_body(corpus_pdf, filename="ar_baseline.pdf"),
        ),
    )
    assert response.status == 422
    assert json.loads(response.body)["error_code"] == "validation_failed"
    after = session.execute(text("SELECT count(*) FROM document_version")).scalar_one()
    assert after == before, "a refused write published something"


def test_an_upload_outside_the_envelope_is_refused(
    router: Router, project: dict[str, Any]
) -> None:
    """A non-PDF is ``validation_failed``. OCR is never silently substituted."""
    response = dispatch(
        router,
        Request.build(
            "POST",
            f"/projects/{project['project_uid']}/documents",
            headers=multipart_headers("journey-not-pdf"),
            body=upload_body(b"this is not a pdf at all", filename="notes.pdf"),
        ),
    )
    assert response.status == 422
    assert json.loads(response.body)["error_code"] == "validation_failed"


# ---------------------------------------------------------------------------
# Streaming
# ---------------------------------------------------------------------------


@pytest.fixture
def published_version(
    router: Router, project: dict[str, Any], corpus_pdf: bytes
) -> dict[str, Any]:
    return ok(
        dispatch(
            router,
            Request.build(
                "POST",
                f"/projects/{project['project_uid']}/documents",
                headers=multipart_headers("journey-stream"),
                body=upload_body(corpus_pdf, filename="ar_baseline.pdf"),
            ),
        )
    )


def test_the_whole_document_streams_back_byte_for_byte(
    router: Router, published_version: dict[str, Any], corpus_pdf: bytes
) -> None:
    response = dispatch(
        router,
        Request.build("GET", f"/versions/{published_version['version_uid']}/content"),
    )
    assert response.status == 200
    assert response.header("Content-Type") == "application/pdf"
    assert response.header("Content-Length") == str(len(corpus_pdf))
    assert response.body == corpus_pdf


@pytest.mark.parametrize(
    "header, expected",
    [
        ("bytes=0-99", (0, 99)),
        ("bytes=100-199", (100, 199)),
        ("bytes=0-0", (0, 0)),
    ],
)
def test_a_byte_range_returns_exactly_that_window(
    router: Router,
    published_version: dict[str, Any],
    corpus_pdf: bytes,
    header: str,
    expected: tuple[int, int],
) -> None:
    response = dispatch(
        router,
        Request.build(
            "GET",
            f"/versions/{published_version['version_uid']}/content",
            headers={"Range": header},
        ),
    )
    start, end = expected
    assert response.status == 206
    assert response.body == corpus_pdf[start : end + 1]
    assert response.header("Content-Range") == f"bytes {start}-{end}/{len(corpus_pdf)}"


def test_an_open_ended_and_a_suffix_range_both_work(
    router: Router, published_version: dict[str, Any], corpus_pdf: bytes
) -> None:
    path = f"/versions/{published_version['version_uid']}/content"

    open_ended = dispatch(
        router, Request.build("GET", path, headers={"Range": "bytes=100-"})
    )
    assert open_ended.status == 206
    assert open_ended.body == corpus_pdf[100:]

    suffix = dispatch(router, Request.build("GET", path, headers={"Range": "bytes=-50"}))
    assert suffix.status == 206
    assert suffix.body == corpus_pdf[-50:]


def test_an_unsatisfiable_range_is_refused_rather_than_answered_in_full(
    router: Router, published_version: dict[str, Any], corpus_pdf: bytes
) -> None:
    """Answering with the whole file would hide the caller's bug behind a big download."""
    for header in ("bytes=999999999-", "bytes=abc", "bytes=-", "bytes=50-10"):
        response = dispatch(
            router,
            Request.build(
                "GET",
                f"/versions/{published_version['version_uid']}/content",
                headers={"Range": header},
            ),
        )
        assert response.status == 422, (header, response.status)
        assert response.body != corpus_pdf


def test_the_content_route_never_redirects(
    router: Router, published_version: dict[str, Any]
) -> None:
    response = dispatch(
        router,
        Request.build("GET", f"/versions/{published_version['version_uid']}/content"),
    )
    assert response.status == 200
    assert response.header("Location") is None


# ---------------------------------------------------------------------------
# Findings and decisions
# ---------------------------------------------------------------------------


def test_findings_list_and_filter(router: Router, published_run: PublishedRun) -> None:
    page = ok(dispatch(router, Request.build("GET", f"/runs/{published_run.run_id}/findings")))
    assert len(page["items"]) == 1
    finding = page["items"][0]
    assert finding["category"] == "internal_contradiction"
    assert finding["current_verdict"] == "pending"
    assert len(finding["observation"]["evidence"]) == 2

    matching = ok(
        dispatch(
            router,
            Request.build(
                "GET",
                f"/runs/{published_run.run_id}/findings?category=internal_contradiction",
            ),
        )
    )
    assert len(matching["items"]) == 1

    other = ok(
        dispatch(
            router,
            Request.build(
                "GET",
                f"/runs/{published_run.run_id}/findings?category=explicit_placeholder",
            ),
        )
    )
    assert other["items"] == []

    rejected = dispatch(
        router,
        Request.build("GET", f"/runs/{published_run.run_id}/findings?category=invented"),
    )
    assert rejected.status == 422


def test_a_decision_moves_the_projection_and_appends_nothing_twice(
    router: Router, published_run: PublishedRun, session: Session
) -> None:
    path = f"/findings/{published_run.finding_uid}/decisions"
    payload = json.dumps(
        {
            "event_type": "reject",
            "finding_observation_id": published_run.finding_observation_id,
            "comment": "Не подтверждено.",
        }
    ).encode("utf-8")

    first = ok(
        dispatch(
            router,
            Request.build("POST", path, headers=json_headers("decide-1"), body=payload),
        )
    )
    assert first["current_verdict"] == "rejected"
    assert first["event"]["verdict"] == "rejected"
    assert first["event"]["author_label"]

    # A replay under the same key appends exactly one event, which the database
    # enforces through the unique index on command_id.
    second = ok(
        dispatch(
            router,
            Request.build("POST", path, headers=json_headers("decide-1"), body=payload),
        )
    )
    assert second["event"]["decision_id"] == first["event"]["decision_id"]

    count = session.execute(
        text("SELECT count(*) FROM expert_decision_event WHERE finding_uid = :f"),
        {"f": published_run.finding_uid},
    ).scalar_one()
    assert count == 1, "the replay appended a second event"

    # An accept after a reject is a third event, not an update.
    accepted = ok(
        dispatch(
            router,
            Request.build(
                "POST",
                path,
                headers=json_headers("decide-2"),
                body=json.dumps(
                    {
                        "event_type": "accept",
                        "finding_observation_id": published_run.finding_observation_id,
                    }
                ).encode("utf-8"),
            ),
        )
    )
    assert accepted["current_verdict"] == "accepted"

    history = ok(dispatch(router, Request.build("GET", path)))
    assert [item["event_type"] for item in history["items"]] == ["reject", "accept"]

    detail = ok(dispatch(router, Request.build("GET", f"/findings/{published_run.finding_uid}")))
    assert detail["current_verdict"] == "accepted"
    assert detail["decision_event_count"] == 2
    assert detail["latest_comment"] == "Не подтверждено."


def test_a_comment_without_a_comment_is_refused(
    router: Router, published_run: PublishedRun
) -> None:
    response = dispatch(
        router,
        Request.build(
            "POST",
            f"/findings/{published_run.finding_uid}/decisions",
            headers=json_headers("decide-3"),
            body=json.dumps(
                {
                    "event_type": "comment",
                    "finding_observation_id": published_run.finding_observation_id,
                }
            ).encode("utf-8"),
        ),
    )
    assert response.status == 422
    assert json.loads(response.body)["error_code"] == "validation_failed"


def test_revoke_is_declared_but_has_no_pc01_producer(
    router: Router, published_run: PublishedRun
) -> None:
    """The enum accepts it at the edge; the ledger refuses to emit one."""
    response = dispatch(
        router,
        Request.build(
            "POST",
            f"/findings/{published_run.finding_uid}/decisions",
            headers=json_headers("decide-4"),
            body=json.dumps(
                {
                    "event_type": "revoke",
                    "finding_observation_id": published_run.finding_observation_id,
                }
            ).encode("utf-8"),
        ),
    )
    assert response.status == 422
    assert json.loads(response.body)["error_code"] == "validation_failed"


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------


def test_the_decision_history_pages_without_losing_or_repeating_an_event(
    router: Router, published_run: PublishedRun
) -> None:
    path = f"/findings/{published_run.finding_uid}/decisions"
    for index in range(5):
        ok(
            dispatch(
                router,
                Request.build(
                    "POST",
                    path,
                    headers=json_headers(f"page-{index}"),
                    body=json.dumps(
                        {
                            "event_type": "comment",
                            "finding_observation_id": published_run.finding_observation_id,
                            "comment": f"Замечание {index}",
                        }
                    ).encode("utf-8"),
                ),
            )
        )

    collected: list[str] = []
    cursor: str | None = None
    for _ in range(10):
        target = f"{path}?limit=2" + (f"&cursor={cursor}" if cursor else "")
        page = ok(dispatch(router, Request.build("GET", target)))
        collected.extend(item["decision_id"] for item in page["items"])
        cursor = page["page"]["next_cursor"]
        if cursor is None:
            break

    assert cursor is None, "the listing never reported a last page"
    assert len(collected) == 5
    assert len(set(collected)) == 5, "an event appeared on two pages"

    whole = ok(dispatch(router, Request.build("GET", path)))
    assert collected == [item["decision_id"] for item in whole["items"]]


def test_no_cursor_carries_a_row_sequence(
    router: Router, published_run: PublishedRun, session: Session
) -> None:
    """The server's ``sequence_no`` is never embedded in a continuation token."""
    path = f"/findings/{published_run.finding_uid}/decisions"
    for index in range(3):
        ok(
            dispatch(
                router,
                Request.build(
                    "POST",
                    path,
                    headers=json_headers(f"seq-{index}"),
                    body=json.dumps(
                        {
                            "event_type": "comment",
                            "finding_observation_id": published_run.finding_observation_id,
                            "comment": f"Заметка {index}",
                        }
                    ).encode("utf-8"),
                ),
            )
        )
    page = ok(dispatch(router, Request.build("GET", f"{path}?limit=1")))
    cursor = page["page"]["next_cursor"]
    assert cursor

    import base64

    decoded = json.loads(
        base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode("utf-8")
    )

    # Structural, not a substring search: `sequence_no` starts at 1 for a fresh
    # ledger, and "1" occurs in any ISO timestamp, so a substring check here would
    # pass or fail for reasons unrelated to the claim. The claim is that the token
    # carries the declared sort key `(recorded_at, decision_id)` and nothing else.
    emitted = page["items"][0]
    assert decoded == [emitted["recorded_at"], emitted["decision_id"]], (
        f"the cursor carries something other than the declared sort key: {decoded}"
    )

    # And the sequence really exists to be leaked, so the assertion is not vacuous.
    sequences = (
        session.execute(
            text("SELECT sequence_no FROM expert_decision_event WHERE finding_uid = :f"),
            {"f": published_run.finding_uid},
        )
        .scalars()
        .all()
    )
    assert sequences, "no events, so nothing could have leaked"
    assert "sequence" not in json.dumps(page).lower()


def test_a_forged_cursor_is_refused(router: Router, published_run: PublishedRun) -> None:
    response = dispatch(
        router,
        Request.build(
            "GET", f"/findings/{published_run.finding_uid}/decisions?cursor=not-a-token"
        ),
    )
    assert response.status == 422
    assert json.loads(response.body)["error_code"] == "validation_failed"


# ---------------------------------------------------------------------------
# Export policy
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("state", ["created", "queued", "running", "validating", "failed"])
def test_a_run_whose_terminal_publishes_no_result_is_refused(
    router: Router, session: Session, state: str
) -> None:
    """``state_transition_not_allowed`` verbatim, never a generic internal error."""
    run = PublishedRun(session, state=state)
    response = dispatch(router, Request.build("GET", f"/runs/{run.run_id}/export.csv"))

    assert response.status == 409, (state, response.body)
    body = json.loads(response.body)
    assert body["error_code"] == "state_transition_not_allowed"
    assert body["retryable"] is False


def test_a_published_run_exports(router: Router, session: Session) -> None:
    run = PublishedRun(session, state="published")
    response = dispatch(router, Request.build("GET", f"/runs/{run.run_id}/export.csv"))

    assert response.status == 200, response.body
    assert response.header("Content-Type") == "text/csv; charset=utf-8"
    assert response.body.startswith("﻿".encode("utf-8")), "the CSV carries no BOM"
    assert b"\r\n" in response.body

    repeated = dispatch(router, Request.build("GET", f"/runs/{run.run_id}/export.csv"))
    assert repeated.body == response.body, "a repeat is not byte-identical"


def test_the_export_router_adds_nothing_to_the_bytes(
    router: Router, session: Session
) -> None:
    """The response body is exactly what the export use case returned."""
    from .conftest import SeamExportAdapter

    run = PublishedRun(session, state="published")
    expected = SeamExportAdapter(session).export_run_csv(run_id=run.run_id)
    response = dispatch(router, Request.build("GET", f"/runs/{run.run_id}/export.csv"))
    assert response.body == expected


def test_an_unknown_run_is_not_found_not_a_refusal(router: Router) -> None:
    response = dispatch(
        router,
        Request.build("GET", "/runs/run_01M2545JSD15ETSNNV904X991K/export.csv"),
    )
    assert response.status == 404
    assert json.loads(response.body)["error_code"] == "not_found"
