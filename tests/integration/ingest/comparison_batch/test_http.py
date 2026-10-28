"""`CMP-INGEST-02`: the six operations over HTTP, on the composed application (real PostgreSQL, real MinIO).

The application is built the way the deployment builds it (``create_app``) but pointed at this suite's throwaway database and
bucket. Two accounts: an **expert** (every operation) and an **administrator without the expert role** (reads only: ADR-0025
decision 16). The batch is declared, sent and confirmed over HTTP too, so the two hooks the adapter runs (after a
declaration, after a confirmation) are what makes the queue rows the assertions read.
"""

from __future__ import annotations

import os
from typing import Any

import pytest
from sqlalchemy import text
from starlette.testclient import TestClient

from auditmanager.api.app import create_app, create_asgi_app
from auditmanager.api.security import API_TOKEN_VARIABLE, Subject, build_signer
from tests.integration.ingest.comparison_batch.support import distinct_pdf
from tests.integration.ingest.comparison_pdf.support import parts_of, sha256

SECRET = "comparison-batch-http-suite"
SEEN_PROJECT = "prj_01ARZ3NDEKTSV4RRFFQ69G5FAV"


def _token(session_factory, label: str, roles: tuple[str, ...]) -> str:
    from auditmanager.access.accounts import AccountRepository
    from auditmanager.access.repository import UserRepository
    from tests.support.accounts import SUITE_NAMES, SUITE_PASSWORD, suite_login

    users = UserRepository()
    with session_factory() as session:
        record = users.find_by_login(session, suite_login(label))
        if record is None:
            created = users.create_user(session, suite_login(label), SUITE_PASSWORD)
            accounts = AccountRepository()
            accounts.complete_profile(session, user_uid=str(created.user_uid), email=None,
                                      last_name=SUITE_NAMES[0], first_name=SUITE_NAMES[1])
            for role in roles:
                accounts.grant_role(session, user_uid=str(created.user_uid), role=role, granted_by=None)
            record = users.find_by_login(session, suite_login(label))
            session.commit()
        signer = build_signer({API_TOKEN_VARIABLE: SECRET})
        return signer.issue(
            Subject(user_uid=str(record.user_uid), login=record.login, token_epoch=record.token_epoch,
                    display_label=record.display_label),
            is_default_credential=False,
        ).token


@pytest.fixture
def api(ingest_database, s3_settings, session_factory):
    environ = {k: v for k, v in os.environ.items()} | {
        "DATABASE_URL": ingest_database.url.render_as_string(hide_password=False),
        "S3_BUCKET": s3_settings.bucket,
        API_TOKEN_VARIABLE: SECRET,
    }
    application = create_app(environ=environ)
    return TestClient(create_asgi_app(environ=environ, application=application), raise_server_exceptions=False)


@pytest.fixture
def expert(session_factory) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(session_factory, 'http-expert-batch', ('expert',))}"}


@pytest.fixture
def admin(session_factory) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(session_factory, 'http-admin-batch', ('admin',))}"}


def _key(label: str) -> dict[str, str]:
    return {"Idempotency-Key": f"http-batch-{label}"}


def _json(response, status: int) -> Any:
    assert response.status_code == status, (response.status_code, response.text[:600])
    return response.json()


def _declare_and_send(api, expert, project, names: list[str], *, label: str) -> str:
    """A batch declared, sent in parts, completed and proposed, all over HTTP."""
    files = {name: distinct_pdf() for name in names}
    declared = [{"display_name": n, "size_bytes": len(d), "sha256": sha256(d)} for n, d in files.items()]
    created = _json(api.post(f"/projects/{project.project_uid}/comparison-uploads", json={"files": declared},
                             headers={**expert, **_key(f"{label}-create")}), 201)
    ids = {item["display_name"]: item["file_id"] for item in created["files"]}
    for index, (name, data) in enumerate(files.items()):
        for number, part in enumerate(parts_of(data), start=1):
            _json(api.put(f"/comparison-uploads/{created['upload_id']}/files/{ids[name]}/parts?part_number={number}",
                          content=part, headers={**expert, **_key(f"{label}-p{index}-{number}"),
                                                 "content-type": "application/octet-stream"}), 200)
        _json(api.post(f"/comparison-uploads/{created['upload_id']}/files/{ids[name]}/completion",
                       headers={**expert, **_key(f"{label}-c{index}")}), 200)
    return created["upload_id"]


def _confirm(api, expert, upload_id: str, one_set: dict, *, label: str) -> Any:
    body = {"files": [{"file_id": f["file_id"], "version_label": f["version_label"]} for f in one_set["files"]]}
    return _json(api.post(f"/comparison-uploads/{upload_id}/sets/{one_set['set_id']}/confirmation", json=body,
                          headers={**expert, **_key(label)}), 200)


def _rows(session_factory, sql: str, **params: Any) -> list[tuple]:
    with session_factory() as session:
        return [tuple(row) for row in session.execute(text(sql), params).all()]


class TestTheWholeBatchOverHttp:
    def test_declare_confirm_pause_resume_exclude_retry_cancel_and_list(self, api, expert, project, session_factory) -> None:
        upload_id = _declare_and_send(api, expert, project, ["Alpha (1).pdf", "Beta (1).pdf", "Gamma (1).pdf"], label="flow")
        # The hook after the declaration gave the batch its drive.
        assert _rows(session_factory, "SELECT count(*) FROM comparison_work WHERE kind = 'comparison_batch_drive'") == [(1,)]

        sets = _json(api.get(f"/comparison-uploads/{upload_id}/proposal", headers=expert), 200)["sets"]
        alpha, beta, gamma = sets
        listed = _json(api.get(f"/projects/{project.project_uid}/comparison-uploads", headers=expert), 200)
        assert [(i["upload_id"], i["state"]) for i in listed["items"]] == [(upload_id, "proposed")]
        assert "files" not in listed["items"][0], "the listing carries no files"
        assert listed["page"].get("next_cursor") is None

        confirmed = _confirm(api, expert, upload_id, alpha, label="confirm-alpha")
        assert confirmed["state"] == "done" and confirmed["document_uid"]
        assert _rows(session_factory, "SELECT kind, state, comparison_upload_id FROM comparison_work WHERE kind = 'page_profile'") == [
            ("page_profile", "queued", upload_id)], "the hook after the confirmation put its version on the queue"
        assert _json(api.get(f"/comparison-uploads/{upload_id}", headers=expert), 200)["state"] == "processing"

        paused = _json(api.post(f"/comparison-uploads/{upload_id}/pause", headers={**expert, **_key("pause")}), 200)
        assert paused["state"] == "paused" and paused["upload_id"] == upload_id and "files" in paused
        resumed = _json(api.post(f"/comparison-uploads/{upload_id}/resume", headers={**expert, **_key("resume")}), 200)
        assert resumed["state"] == "processing"

        left_out = _json(api.post(f"/comparison-uploads/{upload_id}/sets/{beta['set_id']}/exclusion",
                                  headers={**expert, **_key("exclude")}), 200)
        assert left_out["state"] == "excluded" and left_out["set_id"] == beta["set_id"]
        refused = _json(api.post(f"/comparison-uploads/{upload_id}/sets/{gamma['set_id']}/retry",
                                 headers={**expert, **_key("retry")}), 409)
        assert refused["error_code"] == "conflict" and refused["details"]["conflict_reason"] == "comparison_set_state"

        cancelled = _json(api.post(f"/comparison-uploads/{upload_id}/cancellation", headers={**expert, **_key("cancel")}), 200)
        assert cancelled["state"] == "cancelled"
        assert {r[0] for r in _rows(session_factory, "SELECT state FROM comparison_work WHERE kind = 'page_profile'")} <= {
            "cancelled", "leased", "running"}
        assert _rows(session_factory, "SELECT count(*) FROM document_version") == [(1,)], "Alpha's version stays"
        again = _json(api.post(f"/comparison-uploads/{upload_id}/cancellation", headers={**expert, **_key("cancel-again")}), 409)
        assert again["details"]["conflict_reason"] == "comparison_upload_state"

    def test_a_repeat_under_the_same_key_answers_the_same_body(self, api, expert, project) -> None:
        upload_id = _declare_and_send(api, expert, project, ["Alpha (1).pdf", "Beta (1).pdf"], label="rep")
        alpha, _beta = _json(api.get(f"/comparison-uploads/{upload_id}/proposal", headers=expert), 200)["sets"]
        _confirm(api, expert, upload_id, alpha, label="rep-confirm")
        first = _json(api.post(f"/comparison-uploads/{upload_id}/pause", headers={**expert, **_key("rep-pause")}), 200)
        second = _json(api.post(f"/comparison-uploads/{upload_id}/pause", headers={**expert, **_key("rep-pause")}), 200)
        assert first == second and first["state"] == "paused"
        other = _json(api.post(f"/comparison-uploads/{upload_id}/pause", headers={**expert, **_key("rep-pause-2")}), 409)
        assert other["details"]["conflict_reason"] == "comparison_upload_state"
        # A key belongs to one command type: the same string on another operation is another request.
        assert _json(api.post(f"/comparison-uploads/{upload_id}/resume", headers={**expert, **_key("rep-pause")}), 200)["state"] == "processing"


class TestRolesKeysAndAddresses:
    WRITES = ("pause", "resume", "cancellation")

    @pytest.mark.parametrize("suffix", ["pause", "resume", "cancellation", "sets/{set}/exclusion", "sets/{set}/retry"])
    def test_an_administrator_without_the_expert_role_is_refused_every_write(
        self, api, expert, admin, project, suffix: str
    ) -> None:
        upload_id = _declare_and_send(api, expert, project, ["Alpha (1).pdf", "Beta (1).pdf"], label="adm" + "".join(c for c in suffix if c.isalpha())[:10])
        first = _json(api.get(f"/comparison-uploads/{upload_id}/proposal", headers=expert), 200)["sets"][0]
        path = f"/comparison-uploads/{upload_id}/" + suffix.format(set=first["set_id"])
        refused = _json(api.post(path, headers={**admin, **_key("adm")}), 403)
        assert refused["error_code"] == "permission_denied"
        assert _json(api.get(f"/comparison-uploads/{upload_id}", headers=expert), 200)["state"] == "proposed"

    def test_an_administrator_reads_the_listing(self, api, expert, admin, project) -> None:
        upload_id = _declare_and_send(api, expert, project, ["Alpha (1).pdf"], label="adm-list")
        listed = _json(api.get(f"/projects/{project.project_uid}/comparison-uploads", headers=admin), 200)
        assert [i["upload_id"] for i in listed["items"]] == [upload_id]

    @pytest.mark.parametrize("suffix", ["pause", "resume", "cancellation", "sets/cus_01ARZ3NDEKTSV4RRFFQ69G5FAV/exclusion",
                                        "sets/cus_01ARZ3NDEKTSV4RRFFQ69G5FAV/retry"])
    def test_a_write_without_its_key_is_refused_and_an_unknown_batch_is_not_found(self, api, expert, suffix: str) -> None:
        path = f"/comparison-uploads/cbt_01ARZ3NDEKTSV4RRFFQ69G5FAV/{suffix}"
        assert _json(api.post(path, headers=expert), 422)["error_code"] == "validation_failed"
        assert _json(api.post(path, headers={**expert, **_key("nowhere")}), 404)["error_code"] == "not_found"

    def test_an_unknown_project_is_not_found_and_a_bad_cursor_is_a_validation_failure(self, api, expert, project) -> None:
        assert _json(api.get(f"/projects/{SEEN_PROJECT}/comparison-uploads", headers=expert), 404)["error_code"] == "not_found"
        bad = _json(api.get(f"/projects/{project.project_uid}/comparison-uploads?cursor=not-a-cursor", headers=expert), 422)
        assert bad["error_code"] == "validation_failed" and bad["details"]["field"] == "cursor"


class TestPagingOverHttp:
    def test_the_cursor_continues_the_listing_newest_first(self, api, expert, project) -> None:
        made: list[str] = []
        for index in range(3):
            made.append(_declare_and_send(api, expert, project, [f"Set {index} (1).pdf"], label=f"page{index}"))
            _json(api.post(f"/comparison-uploads/{made[-1]}/cancellation", headers={**expert, **_key(f"page-cancel{index}")}), 200)
        url = f"/projects/{project.project_uid}/comparison-uploads?limit=2"
        first = _json(api.get(url, headers=expert), 200)
        assert [i["upload_id"] for i in first["items"]] == [made[2], made[1]]
        cursor = first["page"]["next_cursor"]
        assert cursor
        second = _json(api.get(f"{url}&cursor={cursor}", headers=expert), 200)
        assert [i["upload_id"] for i in second["items"]] == [made[0]]
        assert second["page"].get("next_cursor") is None
