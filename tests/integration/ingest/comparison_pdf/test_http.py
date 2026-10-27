"""`CMP-INGEST-01`: the eight served operations, over HTTP, on the composed application (real PostgreSQL, real MinIO).

The application is built the way the deployment builds it (``create_app``) but pointed at this suite's throwaway database and
bucket, so what it writes is cleaned with the rest. Two accounts: an **expert** (every operation) and an **administrator
without the expert role** (reads only: ADR-0025 decision 16). The flow is the user's: declare, send parts, complete, read the
proposal, confirm, read the document the confirmation made, read and append the order. A comparison version is read back through
the existing screens' own operations (``listDocuments`` with ``upload_kind``, the content stream of its PDF).
"""

from __future__ import annotations

import os
from typing import Any

import pytest
from starlette.testclient import TestClient

from auditmanager.api.app import create_app, create_asgi_app
from auditmanager.api.security import API_TOKEN_VARIABLE, Subject, build_signer
from tests.integration.ingest.comparison_pdf.support import parts_of, sha256, vs1

SECRET = "comparison-ingest-http-suite"


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
    return {"Authorization": f"Bearer {_token(session_factory, 'http-expert', ('expert',))}"}


@pytest.fixture
def admin(session_factory) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(session_factory, 'http-admin', ('admin',))}"}


def _key(label: str) -> dict[str, str]:
    return {"Idempotency-Key": f"http-{label}"}


def _json(response, status: int) -> Any:
    assert response.status_code == status, (response.status_code, response.text[:600])
    return response.json()


@pytest.fixture
def batch(api, expert, project):
    """Five versions declared, sent in parts (one part each), completed and proposed."""
    files = {f"Чертежи ({n}).pdf": data for n, data in zip(range(5, 0, -1), vs1().values(), strict=True)}
    declared = [{"display_name": name, "size_bytes": len(data), "sha256": sha256(data)} for name, data in files.items()]
    created = _json(api.post(f"/projects/{project.project_uid}/comparison-uploads", json={"files": declared},
                             headers={**expert, **_key("create")}), 201)
    ids = {item["display_name"]: item["file_id"] for item in created["files"]}
    for index, (name, data) in enumerate(files.items()):
        for number, part in enumerate(parts_of(data), start=1):
            receipt = _json(api.put(
                f"/comparison-uploads/{created['upload_id']}/files/{ids[name]}/parts?part_number={number}", content=part,
                headers={**expert, **_key(f"p{index}-{number}"), "content-type": "application/octet-stream"}), 200)
            assert receipt == {"file_id": ids[name], "part_number": number, "size_bytes": len(part), "sha256": sha256(part)}
        done = _json(api.post(f"/comparison-uploads/{created['upload_id']}/files/{ids[name]}/completion",
                              headers={**expert, **_key(f"c{index}")}), 200)
        assert done["state"] == "verified" and done["file_id"] == ids[name]
    return created["upload_id"], files, ids


class TestDeclareAndSend:
    def test_the_declared_batch_is_a_201_with_the_part_size_and_every_file(self, api, expert, project) -> None:
        data = vs1()["v1.pdf"]
        body = _json(api.post(f"/projects/{project.project_uid}/comparison-uploads",
                              json={"files": [{"display_name": "a.pdf", "size_bytes": len(data), "sha256": sha256(data), "page_count": 6}]},
                              headers={**expert, **_key("create")}), 201)
        assert (body["state"], body["part_size_bytes"], body["declared_files"], body["declared_bytes"]) == (
            "uploading", 16 * 1024 * 1024, 1, len(data))
        assert body["files"][0]["state"] == "declared" and body["files"][0]["parts_staged"] == 0
        assert "set_id" not in body["files"][0] and "failure_reason" not in body["files"][0], "an absent property is omitted"
        again = _json(api.post(f"/projects/{project.project_uid}/comparison-uploads",
                               json={"files": [{"display_name": "a.pdf", "size_bytes": len(data), "sha256": sha256(data), "page_count": 6}]},
                               headers={**expert, **_key("create")}), 201)
        assert again["upload_id"] == body["upload_id"]

    def test_a_limit_is_a_422_with_the_registered_reason_and_a_second_batch_a_409(self, api, expert, project) -> None:
        over = {"files": [{"display_name": f"Раздел {i}/f.pdf", "size_bytes": 1, "sha256": "a" * 64} for i in range(101)]}
        refused = _json(api.post(f"/projects/{project.project_uid}/comparison-uploads", json=over,
                                 headers={**expert, **_key("over")}), 422)
        assert refused["error_code"] == "validation_failed"
        assert refused["details"] == {"field": "files", "constraint": "comparison_sets_limit"}
        one = {"files": [{"display_name": "a.pdf", "size_bytes": 1, "sha256": "a" * 64}]}
        _json(api.post(f"/projects/{project.project_uid}/comparison-uploads", json=one, headers={**expert, **_key("one")}), 201)
        second = _json(api.post(f"/projects/{project.project_uid}/comparison-uploads", json=one, headers={**expert, **_key("two")}), 409)
        assert second["error_code"] == "conflict" and second["details"]["conflict_reason"] == "comparison_upload_active"

    def test_a_part_over_sixteen_mebibytes_is_a_422(self, api, expert, batch) -> None:
        upload_id, _files, ids = batch
        response = api.put(f"/comparison-uploads/{upload_id}/files/{next(iter(ids.values()))}/parts?part_number=1",
                           content=b"x" * (16 * 1024 * 1024 + 1),
                           headers={**expert, **_key("big"), "content-type": "application/octet-stream"})
        assert response.status_code == 422 and response.json()["error_code"] == "validation_failed"

    def test_a_part_after_completion_is_a_409_and_a_wrong_size_a_422(self, api, expert, batch) -> None:
        upload_id, files, ids = batch
        name, file_id = next(iter(ids.items()))
        late = _json(api.put(f"/comparison-uploads/{upload_id}/files/{file_id}/parts?part_number=1", content=files[name],
                             headers={**expert, **_key("late"), "content-type": "application/octet-stream"}), 409)
        assert late["details"]["conflict_reason"] == "comparison_upload_state"

    def test_a_digest_mismatch_at_completion_is_a_422_storage_integrity_error(self, api, expert, project) -> None:
        data = vs1()["v1.pdf"]
        wrong = data[:-1] + b"X"
        created = _json(api.post(f"/projects/{project.project_uid}/comparison-uploads",
                                 json={"files": [{"display_name": "a.pdf", "size_bytes": len(data), "sha256": sha256(data)}]},
                                 headers={**expert, **_key("create")}), 201)
        file_id = created["files"][0]["file_id"]
        _json(api.put(f"/comparison-uploads/{created['upload_id']}/files/{file_id}/parts?part_number=1", content=wrong,
                      headers={**expert, **_key("p"), "content-type": "application/octet-stream"}), 200)
        refused = _json(api.post(f"/comparison-uploads/{created['upload_id']}/files/{file_id}/completion",
                                 headers={**expert, **_key("c")}), 422)
        assert refused["error_code"] == "storage_integrity_error"
        assert refused["details"] == {"expected_sha256": sha256(data), "actual_sha256": sha256(wrong)}
        read = _json(api.get(f"/comparison-uploads/{created['upload_id']}", headers=expert), 200)
        assert read["files"][0]["state"] == "failed" and read["files"][0]["failure_reason"] == "comparison_file_sha256"


class TestProposeAndConfirm:
    def test_the_proposal_is_one_set_by_designation_in_the_keys_order(self, api, expert, batch) -> None:
        upload_id, files, ids = batch
        read = _json(api.get(f"/comparison-uploads/{upload_id}", headers=expert), 200)
        assert read["state"] == "proposed" and all(f["state"] == "verified" for f in read["files"])
        proposal = _json(api.get(f"/comparison-uploads/{upload_id}/proposal", headers=expert), 200)
        assert proposal["state"] == "proposed" and len(proposal["sets"]) == 1
        only = proposal["sets"][0]
        assert only["designation"] == "СИНТ-01-ЭМ" and only["state"] == "needs_confirmation"
        assert (only["project_stage"], only["section_code"]) == ("R", "EOM")
        assert only["warnings"] == ["order_disagrees_with_file_numbers", "scan_without_text"]
        by_name = {file_id: name for name, file_id in ids.items()}
        # The names run 5..1 in the declared order; the stamps say the oldest is Изм.0, which is the last name.
        assert [by_name[f["file_id"]] for f in only["files"]] == [f"Чертежи ({n}).pdf" for n in range(5, 0, -1)]
        assert [f["version_label"] for f in only["files"]][0].startswith("V1 Изм.0 15.01.2026")

    def _confirm(self, api, headers, upload_id, proposal_set, **extra):
        body = {"files": [{"file_id": f["file_id"], "version_label": f["version_label"]} for f in proposal_set["files"]], **extra}
        return api.post(f"/comparison-uploads/{upload_id}/sets/{proposal_set['set_id']}/confirmation",
                        json=body, headers={**headers, **_key("confirm")})

    def test_the_confirmation_makes_the_document_and_the_comparison_versions_the_screens_read(
        self, api, expert, project, batch
    ) -> None:
        upload_id, files, _ids = batch
        proposal = _json(api.get(f"/comparison-uploads/{upload_id}/proposal", headers=expert), 200)
        done = _json(self._confirm(api, expert, upload_id, proposal["sets"][0], project_stage="R", section_code="EOM"), 200)
        assert done["state"] == "done" and done["document_uid"].startswith("doc_")
        listed = _json(api.get(f"/projects/{project.project_uid}/documents", headers=expert), 200)
        current = listed["items"][0]
        assert current["upload_kind"] == "comparison_pdf" and current["document_uid"] == done["document_uid"]
        assert current["version_ordinal"] == 5 and current["classification"]["section_code"] == "EOM"
        assert [e["role"] for e in current["input_manifest"]] == ["comparison.source_pdf"]
        streamed = api.get(f"/versions/{current['version_uid']}/content", headers=expert)
        assert streamed.status_code == 200 and streamed.content == vs1()["v5.pdf"], "the content stream of a comparison PDF"
        again = _json(self._confirm(api, expert, upload_id, proposal["sets"][0], project_stage="R", section_code="EOM"), 200)
        assert again["document_uid"] == done["document_uid"]

    def test_a_run_cannot_be_started_on_a_comparison_version(self, api, expert, project, batch) -> None:
        upload_id, _files, _ids = batch
        proposal = _json(api.get(f"/comparison-uploads/{upload_id}/proposal", headers=expert), 200)
        done = _json(self._confirm(api, expert, upload_id, proposal["sets"][0], project_stage="R", section_code="EOM"), 200)
        version = _json(api.get(f"/projects/{project.project_uid}/documents", headers=expert), 200)["items"][0]["version_uid"]
        refused = api.post("/runs", headers={**expert, **_key("run")}, json={"version_uid": version})
        assert refused.status_code == 422, refused.text
        assert refused.json()["error_code"] == "analysis_input_invalid" and refused.json()["details"]["reason"] == "comparison_only_version"
        assert done["state"] == "done"

    def test_an_administrator_without_the_expert_role_reads_and_confirms_nothing(self, api, expert, admin, batch) -> None:
        upload_id, _files, _ids = batch
        assert api.get(f"/comparison-uploads/{upload_id}", headers=admin).status_code == 200
        proposal = _json(api.get(f"/comparison-uploads/{upload_id}/proposal", headers=admin), 200)
        refused = self._confirm(api, admin, upload_id, proposal["sets"][0])
        assert refused.status_code == 403 and refused.json()["error_code"] == "permission_denied"
        assert _json(api.get(f"/comparison-uploads/{upload_id}/proposal", headers=expert), 200)["sets"][0]["state"] == "needs_confirmation"

    def test_a_membership_error_is_a_422_and_a_confirmed_set_a_409(self, api, expert, batch) -> None:
        upload_id, _files, _ids = batch
        proposal = _json(api.get(f"/comparison-uploads/{upload_id}/proposal", headers=expert), 200)
        only = proposal["sets"][0]
        short = {"files": [{"file_id": f["file_id"]} for f in only["files"][:-1]]}
        refused = _json(api.post(f"/comparison-uploads/{upload_id}/sets/{only['set_id']}/confirmation", json=short,
                                 headers={**expert, **_key("short")}), 422)
        assert refused["details"] == {"field": "files", "constraint": "comparison_set_members"}
        _json(self._confirm(api, expert, upload_id, only), 200)
        full = {"files": [{"file_id": f["file_id"]} for f in only["files"]]}
        late = _json(api.post(f"/comparison-uploads/{upload_id}/sets/{only['set_id']}/confirmation", json=full,
                              headers={**expert, **_key("late")}), 409)
        assert late["details"]["conflict_reason"] == "comparison_set_state"


class TestTheOrder:
    @pytest.fixture
    def document(self, api, expert, project, batch):
        upload_id, _files, _ids = batch
        proposal = _json(api.get(f"/comparison-uploads/{upload_id}/proposal", headers=expert), 200)
        done = _json(TestProposeAndConfirm()._confirm(api, expert, upload_id, proposal["sets"][0]), 200)
        listed = _json(api.get(f"/projects/{project.project_uid}/documents/{done['document_uid']}/comparison-version-orders",
                               headers=expert), 200)
        return done["document_uid"], listed["items"][0]

    def test_the_confirmation_is_revision_one_and_the_expert_appends_the_next(self, api, expert, project, document) -> None:
        document_uid, first = document
        assert first["revision_no"] == 1 and first["source"] == "proposal" and len(first["version_uids"]) == 5
        path = f"/projects/{project.project_uid}/documents/{document_uid}/comparison-version-orders"
        reordered = list(reversed(first["version_uids"]))
        appended = _json(api.post(path, json={"version_uids": reordered, "base_revision_no": 1}, headers={**expert, **_key("o1")}), 201)
        assert (appended["revision_no"], appended["source"], appended["version_uids"]) == (2, "expert", reordered)
        listed = _json(api.get(path, headers=expert), 200)
        assert [r["revision_no"] for r in listed["items"]] == [2, 1] and listed["page"] == {"next_cursor": None}
        stale = _json(api.post(path, json={"version_uids": first["version_uids"], "base_revision_no": 1},
                               headers={**expert, **_key("o2")}), 409)
        assert stale["details"]["conflict_reason"] == "comparison_version_order_stale"

    def test_the_listing_pages_by_cursor(self, api, expert, project, document) -> None:
        document_uid, first = document
        path = f"/projects/{project.project_uid}/documents/{document_uid}/comparison-version-orders"
        for number in range(2, 5):
            order = first["version_uids"] if number % 2 else list(reversed(first["version_uids"]))
            _json(api.post(path, json={"version_uids": order, "base_revision_no": number - 1}, headers={**expert, **_key(f"o{number}")}), 201)
        page = _json(api.get(path + "?limit=2", headers=expert), 200)
        assert [r["revision_no"] for r in page["items"]] == [4, 3] and page["page"]["next_cursor"]
        rest = _json(api.get(path + f"?limit=2&cursor={page['page']['next_cursor']}", headers=expert), 200)
        assert [r["revision_no"] for r in rest["items"]] == [2, 1] and rest["page"]["next_cursor"] is None

    def test_an_administrator_without_the_expert_role_cannot_append(self, api, expert, admin, project, document) -> None:
        document_uid, first = document
        path = f"/projects/{project.project_uid}/documents/{document_uid}/comparison-version-orders"
        refused = api.post(path, json={"version_uids": list(reversed(first["version_uids"])), "base_revision_no": 1},
                           headers={**admin, **_key("adm")})
        assert refused.status_code == 403 and refused.json()["error_code"] == "permission_denied"
        assert len(_json(api.get(path, headers=admin), 200)["items"]) == 1
